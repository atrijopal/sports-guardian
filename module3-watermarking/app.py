import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import config
from session_registry import SessionRegistry
from watermark import embedder, extractor

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Module 3 — Source Attribution Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = SessionRegistry()


@app.on_event("startup")
async def startup():
    Path(config.WATERMARKED_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Module 3 ready — port {config.PORT}")


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path("static/index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/api/sessions")
async def list_sessions():
    try:
        return {"sessions": registry.list_sessions()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/embed")
async def embed_endpoint(
    file: UploadFile = File(...),
    viewer_name: str = Form(...),
    account_id: str = Form(""),
    region: str = Form(""),
    platform: str = Form(""),
):
    tmp_upload = None
    try:
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename).suffix or ".mp4"
        tmp_fd, tmp_upload = tempfile.mkstemp(suffix=suffix, dir=config.TEMP_DIR)
        import os
        os.close(tmp_fd)
        with open(tmp_upload, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"[API] Embed request: viewer={viewer_name}, file={file.filename}")
        result = await asyncio.to_thread(
            embedder.embed_full,
            tmp_upload,
            viewer_name,
            registry,
            account_id,
            region,
            platform,
        )

        if "error" in result:
            return JSONResponse(status_code=500, content=result)

        result["download_url"] = f"/api/download/{result['output_filename']}"
        return result

    except Exception as e:
        logger.error(f"[API] Embed error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if tmp_upload and Path(tmp_upload).exists():
            try:
                Path(tmp_upload).unlink()
            except Exception:
                pass


@app.post("/api/extract")
async def extract_endpoint(file: UploadFile = File(...)):
    tmp_upload = None
    try:
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename).suffix or ".mp4"
        tmp_fd, tmp_upload = tempfile.mkstemp(suffix=suffix, dir=config.TEMP_DIR)
        import os
        os.close(tmp_fd)
        with open(tmp_upload, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"[API] Extract request: file={file.filename}")
        result = await asyncio.to_thread(
            extractor.extract_full,
            tmp_upload,
            registry,
        )
        return result

    except Exception as e:
        logger.error(f"[API] Extract error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if tmp_upload and Path(tmp_upload).exists():
            try:
                Path(tmp_upload).unlink()
            except Exception:
                pass


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = Path(config.WATERMARKED_DIR) / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.post("/api/reset")
async def reset():
    try:
        registry.reset()
        wm_dir = Path(config.WATERMARKED_DIR)
        if wm_dir.exists():
            for f in wm_dir.iterdir():
                if f.is_file():
                    f.unlink()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
