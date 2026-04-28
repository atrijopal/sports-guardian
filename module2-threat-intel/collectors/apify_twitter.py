import json
import os
import logging
from datetime import datetime, timezone
import config
from parsers.link_extractor import extract_all
from graph_store import GraphStore

logger = logging.getLogger(__name__)


def _extract_author_handle(tweet: dict) -> str | None:
    for path in [
        lambda t: "@" + t["author"]["userName"],
        lambda t: "@" + t["user"]["screen_name"],
        lambda t: "@" + t["username"],
        lambda t: "@" + t["authorName"],
        lambda t: "@" + t["author_name"],
    ]:
        try:
            result = path(tweet)
            if result and result != "@":
                return result
        except (KeyError, TypeError):
            continue
    return None


def _extract_followers(tweet: dict) -> int:
    for path in [
        lambda t: t["author"]["followers"],
        lambda t: t["user"]["followers_count"],
        lambda t: t["authorFollowers"],
        lambda t: t["author"]["followersCount"],
    ]:
        try:
            return int(path(tweet))
        except (KeyError, TypeError, ValueError):
            continue
    return 0


def search_twitter(graph: GraphStore) -> dict:
    if not config.APIFY_API_TOKEN:
        logger.warning("No Apify token. Skipping Twitter collection.")
        return {"tweets_processed": 0, "nodes_created": 0, "edges_created": 0}

    from apify_client import ApifyClient
    client = ApifyClient(config.APIFY_API_TOKEN)
    all_results = []
    stats = {"tweets_processed": 0, "nodes_created": 0, "edges_created": 0}

    for query in config.TWITTER_QUERIES:
        try:
            run = client.actor(config.APIFY_TWITTER_ACTOR).call(input={
                "searchTerms": [query],
                "maxItems": config.TWITTER_MAX_ITEMS_PER_QUERY,
                "sort": "Latest",
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            all_results.extend(items)
            logger.info(f"Twitter query '{query}': {len(items)} items")
        except Exception as e:
            logger.error(f"Twitter query '{query}' failed: {e}")

    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.RAW_DATA_DIR, "twitter_raw.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    posts_for_nlp = []
    for tweet in all_results:
        author = _extract_author_handle(tweet)
        text = tweet.get("text") or tweet.get("full_text") or ""
        if author and text:
            posts_for_nlp.append({
                "text": text,
                "source": "twitter",
                "author": author,
                "followers": _extract_followers(tweet),
                "verified": tweet.get("isVerified", False),
                "_raw_tweet": tweet,
            })

    from nlp.classifier import classify_posts, process_nlp_results_to_graph
    nlp_results = classify_posts(posts_for_nlp)

    if nlp_results:
        logger.info(f"[NLP] Classified {len(nlp_results)} tweets")
        nlp_stats = process_nlp_results_to_graph(posts_for_nlp, nlp_results, graph, "twitter")
        stats["tweets_processed"] = nlp_stats.get("posts_flagged", 0)
        stats["nodes_created"] = nlp_stats.get("nodes_created", 0)
        stats["edges_created"] = nlp_stats.get("edges_created", 0)
    else:
        logger.info("[FALLBACK] Using regex for Twitter")
        now = datetime.now(timezone.utc).isoformat()
        for post in posts_for_nlp:
            author = post["author"]
            text = post["text"]
            author_id = graph.add_node({
                "type": "twitter_account",
                "label": author,
                "metadata": {"handle": author, "followers": post["followers"], "verified": post["verified"]},
                "first_seen": now, "last_seen": now,
                "source": "apify_twitter", "is_real_data": True,
            })
            stats["nodes_created"] += 1
            extracted = extract_all(text)
            for invite in extracted["invite_links"]:
                lid = graph.add_node({
                    "type": "invite_link", "label": invite["url"],
                    "metadata": {"url": invite["url"], "platform": invite["platform"]},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_twitter", "is_real_data": True,
                })
                graph.add_edge({"source": author_id, "target": lid, "relationship": "posted", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            for d in extracted["domains"]:
                did = graph.add_node({
                    "type": "domain", "label": d["domain"],
                    "metadata": {"tld": d["tld"], "matched_keywords": d.get("matched_keywords", [])},
                    "first_seen": now, "last_seen": now,
                    "source": "apify_twitter", "is_real_data": True,
                })
                graph.add_edge({"source": author_id, "target": did, "relationship": "promotes", "timestamp": now})
                stats["nodes_created"] += 1
                stats["edges_created"] += 1
            stats["tweets_processed"] += 1

    graph.save()
    return stats
