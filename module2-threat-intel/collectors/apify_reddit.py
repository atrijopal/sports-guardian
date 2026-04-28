import json
import os
import logging
from datetime import datetime, timezone
import config
from parsers.link_extractor import extract_all
from graph_store import GraphStore

logger = logging.getLogger(__name__)


def search_reddit(graph: GraphStore) -> dict:
    if not config.APIFY_API_TOKEN:
        logger.warning("No Apify token. Skipping Reddit collection.")
        return {"posts_processed": 0, "nodes_created": 0, "edges_created": 0}

    from apify_client import ApifyClient
    client = ApifyClient(config.APIFY_API_TOKEN)
    all_results = []
    stats = {"posts_processed": 0, "nodes_created": 0, "edges_created": 0}

    try:
        run = client.actor(config.APIFY_REDDIT_ACTOR).call(input={
            "startUrls": [{"url": u} for u in config.REDDIT_SUBREDDITS],
            "searchTerms": config.REDDIT_SEARCH_TERMS,
            "maxItems": config.REDDIT_MAX_ITEMS,
            "type": "posts",
        })
        all_results = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info(f"Reddit: {len(all_results)} items")
    except Exception as e:
        logger.error(f"Reddit collection failed: {e}")

    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.RAW_DATA_DIR, "reddit_raw.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    posts_for_nlp = []
    for post in all_results:
        author = (post.get("author") or post.get("username") or "").strip()
        if not author:
            continue
        author = f"u/{author}" if not author.startswith("u/") else author
        text = (post.get("body") or post.get("selftext") or post.get("title") or "").strip()
        if not text:
            continue
        posts_for_nlp.append({
            "text": text,
            "source": "reddit",
            "author": author,
            "subreddit": post.get("subreddit", ""),
            "_raw": post,
        })

    from nlp.classifier import classify_posts, process_nlp_results_to_graph
    nlp_results = classify_posts(posts_for_nlp)

    if nlp_results:
        nlp_stats = process_nlp_results_to_graph(posts_for_nlp, nlp_results, graph, "reddit")
        stats["posts_processed"] = nlp_stats.get("posts_flagged", 0)
        stats["nodes_created"] = nlp_stats.get("nodes_created", 0)
        stats["edges_created"] = nlp_stats.get("edges_created", 0)
    else:
        logger.info("[FALLBACK] Using regex for Reddit")
        now = datetime.now(timezone.utc).isoformat()
        for post in posts_for_nlp:
            author = post["author"]
            author_id = graph.add_node({
                "type": "reddit_account", "label": author,
                "metadata": {"username": author, "subreddit": post.get("subreddit", "")},
                "first_seen": now, "last_seen": now,
                "source": "apify_reddit", "is_real_data": True,
            })
            stats["nodes_created"] += 1
            extracted = extract_all(post["text"])
            for invite in extracted["invite_links"]:
                lid = graph.add_node({
                    "type": "invite_link", "label": invite["url"],
                    "metadata": {"url": invite["url"], "platform": invite["platform"]},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_reddit", "is_real_data": True,
                })
                graph.add_edge({"source": author_id, "target": lid, "relationship": "posted", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            for d in extracted["domains"]:
                did = graph.add_node({
                    "type": "domain", "label": d["domain"],
                    "metadata": {"tld": d["tld"]},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_reddit", "is_real_data": True,
                })
                graph.add_edge({"source": author_id, "target": did, "relationship": "promotes", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            stats["posts_processed"] += 1

    graph.save()
    return stats
