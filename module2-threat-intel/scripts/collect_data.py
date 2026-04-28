"""
Pre-demo data collection. Run 1-2 hours before demo.
Usage: python scripts/collect_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import config
from graph_store import GraphStore
import scoring
from collectors import apify_twitter, apify_reddit, apify_telegram


def main():
    graph = GraphStore(config.GRAPH_DATA_PATH)

    if not graph.get_all_nodes():
        logger.info("Graph empty — generating synthetic data first...")
        from scripts.generate_synthetic import generate_synthetic_data
        generate_synthetic_data(graph)

    logger.info("=== Starting Apify data collection ===")

    tw_stats = apify_twitter.search_twitter(graph)
    logger.info(f"Twitter: {tw_stats}")

    reddit_stats = apify_reddit.search_reddit(graph)
    logger.info(f"Reddit: {reddit_stats}")

    tg_stats = apify_telegram.scrape_telegram(graph)
    logger.info(f"Telegram: {tg_stats}")

    logger.info("=== Running graph analysis ===")
    scoring.run_all_analysis(graph)

    stats = graph.get_stats()
    logger.info(f"\n=== Final Stats ===\n{stats}")


if __name__ == "__main__":
    main()
