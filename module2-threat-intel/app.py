import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from graph_store import GraphStore
from nlp.domain_classifier import DomainClassifierQueue
from google_services import SafeBrowsingService, YouTubeService, GeminiService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

graph = GraphStore(config.GRAPH_DATA_PATH)
domain_nlp_queue = DomainClassifierQueue()
connected_ws: list[WebSocket] = []

# Global Google service instances (injected in lifespan)
sb_service: SafeBrowsingService | None = None
yt_service: YouTubeService | None = None
gemini_service: GeminiService | None = None

# Cached results
_ai_briefing: dict = {}
_yt_channels: list[dict] = []
_google_api_stats: dict = {
    "safe_browsing": {"checked": 0, "hits": 0},
    "youtube": {"searches": 0, "channels_found": 0},
    "gemini": {"briefings": 0, "profiles": 0, "errors": 0},
}


async def broadcast(msg: dict):
    dead = []
    for ws in connected_ws:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_ws.remove(ws)


async def notify_new_threat(node_data: dict):
    await broadcast({"type": "new_threat", "data": node_data})


certstream_monitor = None


async def _poll_feed_queue():
    while True:
        try:
            if certstream_monitor:
                items = []
                while len(items) < 10:
                    try:
                        item = certstream_monitor.feed_queue.get_nowait()
                        items.append(item)
                    except Exception:
                        break
                if items:
                    for item in items:
                        await broadcast({"type": "feed_domain", "data": item})
        except Exception as e:
            logger.error(f"feed_queue poll error: {e}")
        await asyncio.sleep(0.3)


async def _poll_notify_queue():
    while True:
        try:
            if certstream_monitor:
                while True:
                    try:
                        item = certstream_monitor.notify_queue.get_nowait()
                        alert_type = item.pop("_alert_type", "new_threat")
                        await broadcast({"type": alert_type, "data": item})
                    except Exception:
                        break
        except Exception as e:
            logger.error(f"notify_queue poll error: {e}")
        await asyncio.sleep(0.5)


async def _tier2_batch_processor():
    while True:
        await asyncio.sleep(config.CERT_TIER2_BATCH_INTERVAL)
        try:
            await domain_nlp_queue.process_batch(graph, notify_callback=notify_new_threat)
            if certstream_monitor:
                while True:
                    try:
                        item = certstream_monitor.tier2_queue.get_nowait()
                        domain_nlp_queue.enqueue(
                            item["domain"], item["tier1_score"], item["tier1_reasons"]
                        )
                    except Exception:
                        break
        except Exception as e:
            logger.error(f"Tier2 batch error: {e}")


async def _stats_broadcast():
    while True:
        await asyncio.sleep(30)
        try:
            stats = graph.get_stats()
            if certstream_monitor:
                stats["certstream"] = certstream_monitor.get_stats()
            stats["nlp"] = domain_nlp_queue.stats
            stats["google_apis"] = _google_api_stats
            await broadcast({"type": "stats_update", "data": stats})
        except Exception as e:
            logger.error(f"Stats broadcast error: {e}")


async def _safe_browsing_sweep():
    """Full Safe Browsing sweep of all domain nodes every SB_SWEEP_INTERVAL seconds."""
    global _google_api_stats
    while True:
        await asyncio.sleep(config.SB_SWEEP_INTERVAL)
        if not sb_service:
            continue
        try:
            domain_nodes = graph.get_nodes_by_type("domain")
            if not domain_nodes:
                continue
            domains = [n.get("label", "") for n in domain_nodes if n.get("label")]
            hits = await asyncio.to_thread(sb_service.check_domains, domains)
            _google_api_stats["safe_browsing"] = sb_service.stats.copy()

            confirmed = []
            for node in domain_nodes:
                label = node.get("label", "")
                if label in hits:
                    node.setdefault("metadata", {})
                    node["metadata"].update(hits[label])
                    node["metadata"]["google_confirmed"] = True
                    node["threat_score"] = 100.0
                    confirmed.append(label)
                    logger.warning("[SB-Sweep] Confirmed threat: %s", label)

            if hits:
                graph.save()

            await broadcast({
                "type": "sb_sweep_complete",
                "data": {
                    "checked": len(domains),
                    "confirmed": len(confirmed),
                    "threats": confirmed,
                    "ts": datetime.now(timezone.utc).isoformat(),
                },
            })
            logger.info("[SB-Sweep] Checked %d domains, %d hits", len(domains), len(hits))
        except Exception as e:
            logger.error("[SB-Sweep] Error: %s", e)


async def _gemini_briefing_task():
    """Regenerate AI threat briefing every AI_BRIEFING_INTERVAL seconds."""
    global _ai_briefing, _google_api_stats
    await asyncio.sleep(10)  # short initial delay so graph is populated
    while True:
        if gemini_service:
            try:
                stats = graph.get_stats()
                if certstream_monitor:
                    stats["certstream"] = certstream_monitor.get_stats()
                nodes = graph.get_all_nodes()
                top_threats = sorted(nodes, key=lambda n: n.get("threat_score", 0), reverse=True)[:10]
                briefing = await asyncio.to_thread(gemini_service.generate_briefing, stats, top_threats)
                briefing["timestamp"] = datetime.now(timezone.utc).isoformat()
                _ai_briefing = briefing
                _google_api_stats["gemini"] = gemini_service.stats.copy()
                await broadcast({"type": "briefing_updated", "data": briefing})
                logger.info("[Gemini] Briefing updated — level: %s", briefing.get("threat_level"))
            except Exception as e:
                logger.error("[Gemini] Briefing task error: %s", e)
        await asyncio.sleep(config.AI_BRIEFING_INTERVAL)


async def _youtube_hunt_task():
    """Periodic YouTube piracy channel hunt every YT_HUNT_INTERVAL seconds."""
    global _yt_channels, _google_api_stats
    await asyncio.sleep(20)  # initial delay
    while True:
        if yt_service:
            try:
                results = await asyncio.to_thread(
                    yt_service.hunt_piracy_channels,
                    config.YOUTUBE_HUNT_QUERIES,
                    config.YOUTUBE_MAX_HUNT_RESULTS,
                )
                _yt_channels = results
                _google_api_stats["youtube"] = yt_service.stats.copy()

                # Add YouTube channels to graph
                for ch in results:
                    node_id = f"yt_{ch['channel_id']}"
                    existing = graph.get_node(node_id)
                    if not existing:
                        graph.add_node({
                            "id": node_id,
                            "type": "youtube_channel",
                            "label": ch["channel"][:40],
                            "threat_score": ch.get("suspicious_score", 0) * 10,
                            "lifecycle_stage": "active",
                            "first_seen": datetime.now(timezone.utc).isoformat(),
                            "last_seen": datetime.now(timezone.utc).isoformat(),
                            "metadata": {
                                "channel_id": ch["channel_id"],
                                "url": ch["channel_url"],
                                "suspicious_score": ch["suspicious_score"],
                                "sample_title": ch["title"][:80],
                                "query": ch["query"],
                                "thumbnail": ch.get("thumbnail", ""),
                            },
                        })

                await broadcast({"type": "youtube_channels_updated", "data": {
                    "count": len(results),
                    "channels": results[:20],
                    "ts": datetime.now(timezone.utc).isoformat(),
                }})
                logger.info("[YT-Hunt] Found %d channels", len(results))
            except Exception as e:
                logger.error("[YT-Hunt] Error: %s", e)
        await asyncio.sleep(config.YT_HUNT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global certstream_monitor, sb_service, yt_service, gemini_service

    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)

    # Init Google services
    try:
        sb_service = SafeBrowsingService(config.SAFE_BROWSING_API_KEY)
        logger.info("SafeBrowsingService initialized")
    except Exception as e:
        logger.error("SafeBrowsingService init failed: %s", e)

    try:
        yt_service = YouTubeService(config.YOUTUBE_API_KEY)
        logger.info("YouTubeService initialized")
    except Exception as e:
        logger.error("YouTubeService init failed: %s", e)

    try:
        gemini_service = GeminiService(config.GEMINI_API_KEY, config.GEMINI_MODEL)
        logger.info("GeminiService initialized")
    except Exception as e:
        logger.error("GeminiService init failed: %s", e)

    if not graph.get_all_nodes():
        logger.info("Graph empty — generating synthetic data...")
        try:
            from scripts.generate_synthetic import generate_synthetic_data
            generate_synthetic_data(graph)
        except Exception as e:
            logger.error(f"Synthetic generation failed: {e}")

    from collectors.certstream_monitor import CertstreamMonitor
    certstream_monitor = CertstreamMonitor(graph, notify_callback=notify_new_threat)
    if sb_service:
        certstream_monitor.inject_sb_service(sb_service)

    try:
        certstream_monitor.start()
        logger.info("Certstream started (real)")
    except Exception as e:
        logger.warning(f"Certstream start failed: {e}. Starting fake certstream.")
        _start_fake_certstream(certstream_monitor)

    asyncio.create_task(_poll_feed_queue())
    asyncio.create_task(_poll_notify_queue())
    asyncio.create_task(_tier2_batch_processor())
    asyncio.create_task(_stats_broadcast())
    asyncio.create_task(_safe_browsing_sweep())
    asyncio.create_task(_gemini_briefing_task())
    asyncio.create_task(_youtube_hunt_task())

    logger.info(f"Server ready. Graph: {len(graph.get_all_nodes())} nodes")
    yield
    if certstream_monitor:
        certstream_monitor.stop()


def _start_fake_certstream(monitor):
    import threading
    from collectors.fake_certstream import run_fake_certstream
    t = threading.Thread(
        target=run_fake_certstream,
        args=(monitor.feed_queue, monitor.tier2_queue, monitor.score_domain, config.CERT_TIER1_FLAG_THRESHOLD),
        daemon=True,
    )
    t.start()
    logger.info("Fake certstream started as fallback")


app = FastAPI(title="Piracy Intelligence War Room", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("static/index.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)


@app.get("/api/graph")
async def get_graph():
    try:
        return {"nodes": graph.get_all_nodes(), "edges": graph.get_all_edges()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/stats")
async def get_stats():
    try:
        stats = graph.get_stats()
        if certstream_monitor:
            stats["certstream"] = certstream_monitor.get_stats()
        stats["nlp"] = domain_nlp_queue.stats
        stats["google_apis"] = _google_api_stats
        return stats
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/node/{node_id}")
async def get_node(node_id: str):
    try:
        node = graph.get_node(node_id)
        if not node:
            return JSONResponse({"error": "Node not found"}, status_code=404)
        edges = graph.get_edges_for_node(node_id)
        neighbors = graph.get_neighbors(node_id)
        from scoring import compute_velocity
        velocity = compute_velocity(graph, node_id)
        return {"node": node, "edges": edges, "neighbors": neighbors, "velocity": velocity}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/cluster/{cluster_id}")
async def get_cluster(cluster_id: str):
    try:
        nodes = graph.get_nodes_by_cluster(cluster_id)
        node_ids = {n["id"] for n in nodes}
        edges = [e for e in graph.get_all_edges()
                 if e["source"] in node_ids or e["target"] in node_ids]
        return {"cluster_id": cluster_id, "nodes": nodes, "edges": edges}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/certstream/stats")
async def get_certstream_stats():
    try:
        if certstream_monitor:
            return certstream_monitor.get_stats()
        return {"error": "certstream not running"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/ai-briefing")
async def get_ai_briefing():
    try:
        if _ai_briefing:
            return _ai_briefing
        if not gemini_service:
            return JSONResponse({"error": "Gemini not available"}, status_code=503)
        stats = graph.get_stats()
        if certstream_monitor:
            stats["certstream"] = certstream_monitor.get_stats()
        nodes = graph.get_all_nodes()
        top_threats = sorted(nodes, key=lambda n: n.get("threat_score", 0), reverse=True)[:10]
        briefing = await asyncio.to_thread(gemini_service.generate_briefing, stats, top_threats)
        briefing["timestamp"] = datetime.now(timezone.utc).isoformat()
        return briefing
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/operator-profile/{node_id}")
async def get_operator_profile(node_id: str):
    try:
        if not gemini_service:
            return JSONResponse({"error": "Gemini not available"}, status_code=503)
        node = graph.get_node(node_id)
        if not node:
            return JSONResponse({"error": "Node not found"}, status_code=404)
        neighbors = graph.get_neighbors(node_id)
        edges = graph.get_edges_for_node(node_id)
        profile = await asyncio.to_thread(
            gemini_service.generate_operator_profile, node, neighbors, len(edges)
        )
        return {"node_id": node_id, "profile": profile}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/youtube-channels")
async def get_youtube_channels():
    try:
        return {"channels": _yt_channels, "count": len(_yt_channels)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/google-status")
async def get_google_status():
    try:
        return {
            "safe_browsing": {
                "enabled": sb_service is not None,
                "stats": sb_service.stats if sb_service else {},
            },
            "youtube": {
                "enabled": yt_service is not None,
                "stats": yt_service.stats if yt_service else {},
            },
            "gemini": {
                "enabled": gemini_service is not None,
                "model": config.GEMINI_MODEL,
                "stats": gemini_service.stats if gemini_service else {},
            },
            "certstream_sb_hits": certstream_monitor.stats.get("sb_realtime_hits", 0) if certstream_monitor else 0,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/threat-feed")
async def get_threat_feed():
    try:
        nodes = graph.get_all_nodes()
        threats = sorted(
            [n for n in nodes if n.get("threat_score", 0) > 20],
            key=lambda n: n.get("threat_score", 0),
            reverse=True,
        )[:50]
        return {"threats": threats, "total": len(threats)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/reset")
async def reset_graph():
    try:
        graph.reset()
        from scripts.generate_synthetic import generate_synthetic_data
        generate_synthetic_data(graph)
        return {"status": "reset", "nodes": len(graph.get_all_nodes())}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/collect")
async def collect_data():
    try:
        from collectors import apify_twitter, apify_reddit, apify_telegram
        import scoring

        tw = await asyncio.to_thread(apify_twitter.search_twitter, graph)
        rd = await asyncio.to_thread(apify_reddit.search_reddit, graph)
        tg = await asyncio.to_thread(apify_telegram.scrape_telegram, graph)
        await asyncio.to_thread(scoring.run_all_analysis, graph)
        return {"twitter": tw, "reddit": rd, "telegram": tg, "stats": graph.get_stats()}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws.accept()
    connected_ws.append(ws)
    logger.info(f"WebSocket connected. Total: {len(connected_ws)}")
    try:
        # Send initial state on connect
        stats = graph.get_stats()
        if certstream_monitor:
            stats["certstream"] = certstream_monitor.get_stats()
        stats["google_apis"] = _google_api_stats
        await ws.send_json({"type": "init", "data": {
            "stats": stats,
            "briefing": _ai_briefing,
            "yt_channels": _yt_channels[:10],
        }})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in connected_ws:
            connected_ws.remove(ws)
        logger.info(f"WebSocket disconnected. Total: {len(connected_ws)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=True)
