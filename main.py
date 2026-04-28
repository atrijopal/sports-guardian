import asyncio
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent

MODULES = {
    "m1": {"dir": BASE / "module1-fingerprinting", "port": 8001},
    "m2": {"dir": BASE / "module2-threat-intel",   "port": 8002},
    "m3": {"dir": BASE / "module3-watermarking",   "port": 8003},
}

_procs: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    for name, svc in MODULES.items():
        log.info("Starting %s on internal port %d", name, svc["port"])
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app",
             "--host", "127.0.0.1", "--port", str(svc["port"]), "--log-level", "warning"],
            cwd=str(svc["dir"]),
        )
        _procs[name] = p
    log.info("All modules launched — main app ready on $PORT")
    yield
    for name, p in _procs.items():
        log.info("Stopping %s", name)
        p.terminate()


app = FastAPI(title="Sports Guardian", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def hub():
    return HTMLResponse((BASE / "hub" / "static" / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── WebSocket proxy (M2 connects to ws://host/ws/live) ──────────────────────
@app.websocket("/ws/live")
async def ws_proxy(websocket: WebSocket):
    await websocket.accept()
    import websockets as _ws
    try:
        async with _ws.connect("ws://127.0.0.1:8002/ws/live") as upstream:
            async def to_client():
                async for msg in upstream:
                    try:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                    except Exception:
                        return

            async def to_upstream():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await upstream.send(data)
                except Exception:
                    return

            await asyncio.gather(to_client(), to_upstream())
    except Exception as e:
        log.debug("WS proxy closed: %s", e)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── HTTP reverse proxy ───────────────────────────────────────────────────────
async def _proxy(request: Request, prefix: str, port: int) -> Response:
    path = request.url.path[len(f"/{prefix}"):]
    if not path.startswith("/"):
        path = "/" + path
    url = f"http://127.0.0.1:{port}{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host",)}
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            )
        skip = {"transfer-encoding", "connection"}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
        return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)
    except httpx.ConnectError:
        return Response(
            content=b"<html><body style='background:#000;color:#0f0;font-family:monospace;padding:2rem'>"
                    b"<h2>Starting up...</h2><p>Module is still booting. Refresh in a few seconds.</p></body></html>",
            status_code=503,
            media_type="text/html",
        )


@app.api_route("/m1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_m1(request: Request, path: str):
    return await _proxy(request, "m1", 8001)


@app.api_route("/m2/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_m2(request: Request, path: str):
    return await _proxy(request, "m2", 8002)


@app.api_route("/m3/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_m3(request: Request, path: str):
    return await _proxy(request, "m3", 8003)
