"""
Simulates certstream for demo fallback if certstream.calidog.io is down/blocked.
Generates realistic domain alerts every 1-4 seconds.
"""
import random
import time
import threading
from queue import Queue

SUSPICIOUS_TEMPLATES = [
    "{sport}stream-{adj}.{tld}",
    "{sport}live-{adj}.{tld}",
    "free{sport}hd.{tld}",
    "watch{sport}-{adj}.{tld}",
    "{brand}-{suffix}.{tld}",
    "str3am-{sport}.{tld}",
    "{sport}s-fr33.{tld}",
]

BENIGN_DOMAINS = [
    "myshop-store.com", "blog-portfolio.dev", "acme-solutions.io",
    "photography-studio.net", "recipe-tracker.app", "api-gateway.cloud",
    "dental-clinic-nyc.com", "greenleaf-organics.net", "techstartup-hub.io",
    "coffee-roasters-co.com", "event-planner-app.net", "fitness-tracker-pro.io",
    "realestate-listings.com", "online-tutoring-hub.edu", "travel-deals-today.com",
    "home-decor-shop.net", "bookstore-online.io", "restaurant-finder.app",
    "job-portal-pro.com", "news-aggregator.net", "weather-forecast-app.io",
    "stock-market-tracker.com", "music-streaming-svc.net", "gaming-community.gg",
    "cloud-storage-pro.io", "video-editor-online.com", "project-management.app",
    "e-commerce-solutions.net", "digital-marketing-hub.io", "data-analytics.com",
]

SPORTS = ["football", "soccer", "match", "sports", "nba", "ufc", "cricket", "boxing"]
ADJS = ["free", "hd", "live", "today", "new", "v2", "pro", "plus", "ultra"]
TLDS = [".xyz", ".top", ".site", ".online", ".live", ".stream", ".club"]
BRANDS = ["streameast", "sportsurge", "crackstream", "buffstream", "720pstream"]
SUFFIXES = ["hd", "v2", "new", "live", "pro", "today", "2024", "plus"]


def generate_suspicious_domain() -> str:
    template = random.choice(SUSPICIOUS_TEMPLATES)
    return template.format(
        sport=random.choice(SPORTS),
        adj=random.choice(ADJS),
        tld=random.choice(TLDS),
        brand=random.choice(BRANDS),
        suffix=random.choice(SUFFIXES),
    )


def generate_benign_domain() -> str:
    return random.choice(BENIGN_DOMAINS)


def run_fake_certstream(feed_queue: Queue, tier2_queue: Queue, score_fn, flag_threshold: int, interval_range=(1, 4)):
    """
    Generates fake certificate events. Use instead of real certstream.
    score_fn: the CertstreamMonitor.score_domain method
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Fake certstream started (real certstream unavailable)")

    while True:
        time.sleep(random.uniform(*interval_range))
        count = random.randint(1, 3)
        for _ in range(count):
            if random.random() < 0.12:
                domain = generate_suspicious_domain()
            else:
                domain = generate_benign_domain()

            result = score_fn(domain)
            feed_item = {
                "domain": domain,
                "tier1_score": result["score"],
                "flagged": result["flagged"],
                "reasons": result["reasons"],
            }
            try:
                feed_queue.put_nowait(feed_item)
            except Exception:
                pass

            if result["flagged"]:
                tier2_queue.put({
                    "domain": domain,
                    "tier1_score": result["score"],
                    "tier1_reasons": result["reasons"],
                })
