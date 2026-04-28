# app.py — FastAPI server, routes, orchestration

import asyncio
import logging
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Sports Fingerprint Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/list")
def api_list():
    return storage.list_fingerprints()


@app.post("/api/register")
async def api_register(file: UploadFile):
    tmp_path = None
    try:
        # Save upload to temp file
        suffix = Path(file.filename).suffix or ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        tmp_path = Path(tmp_path)
        with open(tmp_fd, "wb") as f:
            shutil.copyfileobj(file.file, f)

        log.info("Registering %s", file.filename)

        # Import layers here to avoid circular issues at startup
        from fingerprint import layer1_visual, layer2_audio, layer4_dna

        log.info("Layer 1: generating visual fingerprint")
        fp1 = await asyncio.to_thread(layer1_visual.generate_fingerprint, str(tmp_path))

        log.info("Layer 2: generating audio fingerprint")
        fp2 = await asyncio.to_thread(layer2_audio.generate_fingerprint, str(tmp_path))

        log.info("Layer 4: generating DNA fingerprint")
        fp4 = await asyncio.to_thread(layer4_dna.generate_fingerprint, str(tmp_path))

        entry = {
            "video_id": str(uuid.uuid4()),
            "name": file.filename,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "duration_sec": fp2.get("duration"),
            "layer1": fp1,
            "layer2": fp2,
            "layer4": fp4,
        }

        storage.add_fingerprint(entry)
        log.info("Registered %s (id=%s)", file.filename, entry["video_id"])

        return {
            "status": "ok",
            "video_id": entry["video_id"],
            "name": entry["name"],
            "duration_sec": entry["duration_sec"],
        }

    except Exception as exc:
        log.exception("Registration failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/check")
async def api_check(file: UploadFile):
    tmp_path = None
    try:
        suffix = Path(file.filename).suffix or ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        tmp_path = Path(tmp_path)
        with open(tmp_fd, "wb") as f:
            shutil.copyfileobj(file.file, f)

        log.info("Checking suspect clip: %s", file.filename)

        from fingerprint import layer1_visual, layer2_audio, layer4_dna, fusion

        log.info("Layer 1: fingerprinting suspect")
        fp1 = await asyncio.to_thread(layer1_visual.generate_fingerprint, str(tmp_path))

        log.info("Layer 2: fingerprinting suspect")
        fp2 = await asyncio.to_thread(layer2_audio.generate_fingerprint, str(tmp_path))

        log.info("Layer 4: fingerprinting suspect")
        fp4 = await asyncio.to_thread(layer4_dna.generate_fingerprint, str(tmp_path))

        suspect_fp = {"layer1": fp1, "layer2": fp2, "layer4": fp4}

        originals = storage.get_all_fingerprints()
        if not originals:
            return {"is_match": False, "verdict": "NO_MATCH", "explanation": "No videos registered yet."}

        log.info("Running fusion against %d registered video(s)", len(originals))
        result = await asyncio.to_thread(fusion.best_match, suspect_fp, originals)

        log.info("Result: %s (score=%.2f)", result.get("verdict"), result.get("overall_score", 0))
        return result

    except Exception as exc:
        log.exception("Check failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/ai-explain")
async def api_ai_explain(request: Request):
    try:
        body = await request.json()
        match_result = body.get("match_result", {})
        suspect_filename = body.get("suspect_filename", "unknown")
        if not match_result:
            return JSONResponse(status_code=400, content={"error": "match_result required"})

        from google_services import generate_ai_analysis
        result = await asyncio.to_thread(generate_ai_analysis, match_result, suspect_filename)
        return result
    except Exception as exc:
        log.exception("AI explain failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/youtube-scan")
async def api_youtube_scan(request: Request):
    try:
        body = await request.json()
        video_name = body.get("video_name", "").strip()
        if not video_name:
            return JSONResponse(status_code=400, content={"error": "video_name required"})

        from google_services import search_youtube_piracy
        results = await asyncio.to_thread(search_youtube_piracy, video_name)
        return {"results": results, "query_video": video_name, "count": len(results)}
    except Exception as exc:
        log.exception("YouTube scan failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/reset")
def api_reset():
    try:
        storage.save_db([])
        log.info("Database reset")
        return {"status": "ok"}
    except Exception as exc:
        log.exception("Reset failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})
