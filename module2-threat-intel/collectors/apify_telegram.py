import json
import os
import logging
from datetime import datetime, timezone
import config
from parsers.link_extractor import extract_all
from graph_store import GraphStore

logger = logging.getLogger(__name__)


def scrape_telegram(graph: GraphStore) -> dict:
    if not config.APIFY_API_TOKEN:
        logger.warning("No Apify token. Skipping Telegram collection.")
        return {"messages_processed": 0, "nodes_created": 0, "edges_created": 0}

    from apify_client import ApifyClient
    client = ApifyClient(config.APIFY_API_TOKEN)
    all_results = []
    stats = {"messages_processed": 0, "nodes_created": 0, "edges_created": 0}

    for channel in config.TELEGRAM_CHANNELS:
        username = channel.lstrip("@")
        try:
            run = client.actor(config.APIFY_TELEGRAM_ACTOR).call(input={
                "channelUsername": username,
                "startMessageId": 1,
                "endMessageId": config.TELEGRAM_MAX_MESSAGES,
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            for item in items:
                item["_channel"] = channel
            all_results.extend(items)
            logger.info(f"Telegram {channel}: {len(items)} messages")
        except Exception as e:
            logger.error(f"Telegram {channel} failed: {e}")

    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.RAW_DATA_DIR, "telegram_raw.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    posts_for_nlp = []
    for msg in all_results:
        text = (msg.get("text") or msg.get("message") or "").strip()
        channel = msg.get("_channel", "unknown")
        if not text:
            continue
        posts_for_nlp.append({
            "text": text,
            "source": "telegram",
            "author": channel,
            "_raw": msg,
        })

    from nlp.classifier import classify_posts, process_nlp_results_to_graph
    nlp_results = classify_posts(posts_for_nlp)

    if nlp_results:
        nlp_stats = process_nlp_results_to_graph(posts_for_nlp, nlp_results, graph, "telegram")
        stats["messages_processed"] = nlp_stats.get("posts_flagged", 0)
        stats["nodes_created"] = nlp_stats.get("nodes_created", 0)
        stats["edges_created"] = nlp_stats.get("edges_created", 0)
    else:
        logger.info("[FALLBACK] Using regex for Telegram")
        now = datetime.now(timezone.utc).isoformat()
        channel_nodes: dict[str, str] = {}
        for post in posts_for_nlp:
            channel = post["author"]
            if channel not in channel_nodes:
                cid = graph.add_node({
                    "type": "telegram_channel", "label": channel,
                    "metadata": {"channel_name": channel},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_telegram", "is_real_data": True,
                })
                channel_nodes[channel] = cid
                stats["nodes_created"] += 1
            else:
                cid = channel_nodes[channel]

            extracted = extract_all(post["text"])
            for invite in extracted["invite_links"]:
                lid = graph.add_node({
                    "type": "invite_link", "label": invite["url"],
                    "metadata": {"url": invite["url"], "platform": invite["platform"]},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_telegram", "is_real_data": True,
                })
                graph.add_edge({"source": cid, "target": lid, "relationship": "posted", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            for d in extracted["domains"]:
                did = graph.add_node({
                    "type": "domain", "label": d["domain"],
                    "metadata": {"tld": d["tld"]},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_telegram", "is_real_data": True,
                })
                graph.add_edge({"source": cid, "target": did, "relationship": "promotes", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            stats["messages_processed"] += 1

    graph.save()
    return stats
