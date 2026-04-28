"""
Generate realistic synthetic demo data: 3 operator clusters + scattered independents.
Run: python scripts/generate_synthetic.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from graph_store import GraphStore
import scoring
import config
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def generate_synthetic_data(graph: GraphStore) -> None:
    # ---- CLUSTER 1: The Streameast Network ----
    d1 = graph.add_node({"type": "domain", "label": "streameast-hd.xyz",
        "metadata": {"tld": ".xyz", "registrar": "NameCheap", "cert_issuer": "Let's Encrypt", "ip": "104.21.11.22"},
        "first_seen": ts(72), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})
    d2 = graph.add_node({"type": "domain", "label": "streameast-live.top",
        "metadata": {"tld": ".top", "registrar": "NameCheap", "cert_issuer": "Let's Encrypt", "ip": "104.21.11.23"},
        "first_seen": ts(70), "last_seen": ts(3), "source": "synthetic", "is_real_data": False})
    d3 = graph.add_node({"type": "domain", "label": "sportshd-free.online",
        "metadata": {"tld": ".online", "registrar": "NameCheap", "cert_issuer": "Let's Encrypt", "ip": "104.21.11.24"},
        "first_seen": ts(68), "last_seen": ts(4), "source": "synthetic", "is_real_data": False})
    d4 = graph.add_node({"type": "domain", "label": "streameast-v2.site",
        "metadata": {"tld": ".site", "registrar": "NameCheap", "cert_issuer": "Let's Encrypt", "ip": "104.21.11.25"},
        "first_seen": ts(48), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})

    tg1 = graph.add_node({"type": "telegram_channel", "label": "@streameast_official",
        "metadata": {"channel_name": "@streameast_official", "subscribers": 45000},
        "first_seen": ts(60), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})
    tg2 = graph.add_node({"type": "telegram_channel", "label": "@sportsHD_links",
        "metadata": {"channel_name": "@sportsHD_links", "subscribers": 28000},
        "first_seen": ts(55), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})
    tg3 = graph.add_node({"type": "telegram_channel", "label": "@freefootball_live",
        "metadata": {"channel_name": "@freefootball_live", "subscribers": 19000},
        "first_seen": ts(50), "last_seen": ts(3), "source": "synthetic", "is_real_data": False})

    tw1 = graph.add_node({"type": "twitter_account", "label": "@streamking2024",
        "metadata": {"handle": "@streamking2024", "followers": 12400, "verified": False,
                     "nlp_intent": "coded_distribution", "nlp_threat_level": "high",
                     "nlp_summary": "Account uses DM-based distribution with coded language",
                     "nlp_threat_signals": ["DM-based distribution", "coded language"]},
        "first_seen": ts(48), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})
    tw2 = graph.add_node({"type": "twitter_account", "label": "@hdmatches_free",
        "metadata": {"handle": "@hdmatches_free", "followers": 8200, "verified": False},
        "first_seen": ts(46), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})
    tw3 = graph.add_node({"type": "twitter_account", "label": "@livesports_247",
        "metadata": {"handle": "@livesports_247", "followers": 5600, "verified": False},
        "first_seen": ts(44), "last_seen": ts(3), "source": "synthetic", "is_real_data": False})
    tw4 = graph.add_node({"type": "twitter_account", "label": "@footystreams99",
        "metadata": {"handle": "@footystreams99", "followers": 3100, "verified": False},
        "first_seen": ts(40), "last_seen": ts(4), "source": "synthetic", "is_real_data": False})
    tw5 = graph.add_node({"type": "twitter_account", "label": "@sportslinkbot",
        "metadata": {"handle": "@sportslinkbot", "followers": 15800, "verified": False},
        "first_seen": ts(38), "last_seen": ts(0.5), "source": "synthetic", "is_real_data": False})

    il1 = graph.add_node({"type": "invite_link", "label": "https://t.me/streameast_official",
        "metadata": {"url": "https://t.me/streameast_official", "platform": "telegram"},
        "first_seen": ts(50), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})
    il2 = graph.add_node({"type": "invite_link", "label": "https://discord.gg/fakeABC123",
        "metadata": {"url": "https://discord.gg/fakeABC123", "platform": "discord"},
        "first_seen": ts(45), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})
    il3 = graph.add_node({"type": "invite_link", "label": "https://t.me/sportsHD_links",
        "metadata": {"url": "https://t.me/sportsHD_links", "platform": "telegram"},
        "first_seen": ts(42), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})

    r1 = graph.add_node({"type": "reddit_account", "label": "u/streamguy99",
        "metadata": {"username": "u/streamguy99", "karma": 2300},
        "first_seen": ts(36), "last_seen": ts(5), "source": "synthetic", "is_real_data": False})
    r2 = graph.add_node({"type": "reddit_account", "label": "u/matchday_links",
        "metadata": {"username": "u/matchday_links", "karma": 870},
        "first_seen": ts(34), "last_seen": ts(6), "source": "synthetic", "is_real_data": False})
    r3 = graph.add_node({"type": "reddit_account", "label": "u/footballfree_hd",
        "metadata": {"username": "u/footballfree_hd", "karma": 450},
        "first_seen": ts(30), "last_seen": ts(7), "source": "synthetic", "is_real_data": False})
    r4 = graph.add_node({"type": "reddit_account", "label": "u/sportshd_bot",
        "metadata": {"username": "u/sportshd_bot", "karma": 1200},
        "first_seen": ts(28), "last_seen": ts(5), "source": "synthetic", "is_real_data": False})

    # Cluster 1 edges
    for tw in [tw1, tw2, tw3]:
        graph.add_edge({"source": tw, "target": il1, "relationship": "posted", "timestamp": ts(24)})
    for tw in [tw4, tw5]:
        graph.add_edge({"source": tw, "target": il2, "relationship": "posted", "timestamp": ts(20)})
    graph.add_edge({"source": tw3, "target": il3, "relationship": "posted", "timestamp": ts(18)})
    graph.add_edge({"source": il1, "target": tg1, "relationship": "links_to", "timestamp": ts(23)})
    graph.add_edge({"source": il3, "target": tg2, "relationship": "links_to", "timestamp": ts(19)})
    for tg in [tg1, tg2, tg3]:
        for d in [d1, d2]:
            graph.add_edge({"source": tg, "target": d, "relationship": "promotes", "timestamp": ts(22)})
    for tw in [tw1, tw2, tw5]:
        graph.add_edge({"source": tw, "target": d3, "relationship": "promotes", "timestamp": ts(20)})
    graph.add_edge({"source": tw4, "target": d4, "relationship": "promotes", "timestamp": ts(15)})
    for r in [r1, r2]:
        graph.add_edge({"source": r, "target": il1, "relationship": "posted", "timestamp": ts(16)})
    for r in [r3, r4]:
        graph.add_edge({"source": r, "target": il3, "relationship": "posted", "timestamp": ts(14)})
    for da, db in [(d1,d2),(d1,d3),(d1,d4),(d2,d3),(d2,d4),(d3,d4)]:
        graph.add_edge({"source": da, "target": db, "relationship": "same_operator", "timestamp": ts(70)})

    # ---- CLUSTER 2: The Telegram Ring ----
    d5 = graph.add_node({"type": "domain", "label": "livematch-hd.site",
        "metadata": {"tld": ".site", "ip": "185.220.101.10"},
        "first_seen": ts(96), "last_seen": ts(8), "source": "synthetic", "is_real_data": False})
    d6 = graph.add_node({"type": "domain", "label": "soccerstreams-today.online",
        "metadata": {"tld": ".online", "ip": "185.220.101.11"},
        "first_seen": ts(90), "last_seen": ts(6), "source": "synthetic", "is_real_data": False})

    tg_ring = []
    ring_names = ["@soccer_streams_ring", "@match_links_daily", "@hd_streams_tg",
                  "@football_links_vip", "@sport_updates_live", "@freematch_channel"]
    ring_subs = [32000, 18000, 45000, 12000, 27000, 9000]
    for name, subs in zip(ring_names, ring_subs):
        nid = graph.add_node({"type": "telegram_channel", "label": name,
            "metadata": {"channel_name": name, "subscribers": subs},
            "first_seen": ts(80), "last_seen": ts(4), "source": "synthetic", "is_real_data": False})
        tg_ring.append(nid)

    tw_ring = []
    for handle, followers in [("@ringmaster_hd",22000),("@sportsfeed_live",9400),("@matchlinks_bot",6700),("@tgstreams_today",4200)]:
        nid = graph.add_node({"type": "twitter_account", "label": handle,
            "metadata": {"handle": handle, "followers": followers},
            "first_seen": ts(72), "last_seen": ts(5), "source": "synthetic", "is_real_data": False})
        tw_ring.append(nid)

    il_ring = []
    for url, platform in [("https://t.me/soccer_streams_ring","telegram"),("https://t.me/hd_streams_tg","telegram"),("https://t.me/football_links_vip","telegram")]:
        nid = graph.add_node({"type": "invite_link", "label": url,
            "metadata": {"url": url, "platform": platform},
            "first_seen": ts(70), "last_seen": ts(4), "source": "synthetic", "is_real_data": False})
        il_ring.append(nid)

    for i in range(len(tg_ring)):
        for j in range(i+1, min(i+3, len(tg_ring))):
            graph.add_edge({"source": tg_ring[i], "target": tg_ring[j], "relationship": "cross_posts", "timestamp": ts(48)})
    for tg in tg_ring[:3]:
        graph.add_edge({"source": tg, "target": d5, "relationship": "promotes", "timestamp": ts(40)})
    for tg in tg_ring[3:]:
        graph.add_edge({"source": tg, "target": d6, "relationship": "promotes", "timestamp": ts(35)})
    for tw, il in zip(tw_ring, il_ring):
        graph.add_edge({"source": tw, "target": il, "relationship": "posted", "timestamp": ts(30)})
    for il, tg in zip(il_ring, tg_ring):
        graph.add_edge({"source": il, "target": tg, "relationship": "links_to", "timestamp": ts(29)})
    graph.add_edge({"source": d5, "target": d6, "relationship": "same_operator", "timestamp": ts(90)})

    # ---- CLUSTER 3: The Lone Wolf (migration pattern) ----
    lw = graph.add_node({"type": "twitter_account", "label": "@megastreams_io",
        "metadata": {"handle": "@megastreams_io", "followers": 42000, "verified": False,
                     "nlp_intent": "promotion", "nlp_threat_level": "critical",
                     "nlp_summary": "High-follower account operating multiple rotating stream domains",
                     "nlp_threat_signals": ["domain rotation", "evasion pattern", "high reach"]},
        "first_seen": ts(336), "last_seen": ts(0.5), "source": "synthetic", "is_real_data": False})

    lw_domains = [
        ("megastreams.xyz", ts(288), ts(276), "dormant"),
        ("megastreams-v2.top", ts(192), ts(180), "dormant"),
        ("megastreams-hd.live", ts(72), ts(60), "dormant"),
        ("megastreams-new.site", ts(12), ts(2), "active"),
    ]
    lw_domain_ids = []
    for label, first, last, stage in lw_domains:
        tld = "." + label.rsplit(".", 1)[-1]
        nid = graph.add_node({"type": "domain", "label": label,
            "metadata": {"tld": tld, "registrar": "NameCheap"},
            "first_seen": first, "last_seen": last,
            "lifecycle_stage": stage,
            "source": "synthetic", "is_real_data": False})
        lw_domain_ids.append(nid)
        graph.add_edge({"source": lw, "target": nid, "relationship": "promotes", "timestamp": first})

    lw_il1 = graph.add_node({"type": "invite_link", "label": "https://t.me/megastreams_official",
        "metadata": {"url": "https://t.me/megastreams_official", "platform": "telegram"},
        "first_seen": ts(200), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})
    lw_il2 = graph.add_node({"type": "invite_link", "label": "https://discord.gg/megastreams",
        "metadata": {"url": "https://discord.gg/megastreams", "platform": "discord"},
        "first_seen": ts(100), "last_seen": ts(2), "source": "synthetic", "is_real_data": False})
    lw_tg = graph.add_node({"type": "telegram_channel", "label": "@megastreams_official",
        "metadata": {"channel_name": "@megastreams_official", "subscribers": 67000},
        "first_seen": ts(300), "last_seen": ts(1), "source": "synthetic", "is_real_data": False})

    graph.add_edge({"source": lw, "target": lw_il1, "relationship": "posted", "timestamp": ts(50)})
    graph.add_edge({"source": lw, "target": lw_il2, "relationship": "posted", "timestamp": ts(30)})
    graph.add_edge({"source": lw_il1, "target": lw_tg, "relationship": "links_to", "timestamp": ts(49)})
    graph.add_edge({"source": lw_tg, "target": lw_domain_ids[-1], "relationship": "promotes", "timestamp": ts(10)})
    for i in range(len(lw_domain_ids)-1):
        graph.add_edge({"source": lw_domain_ids[i], "target": lw_domain_ids[i+1],
                        "relationship": "same_operator", "timestamp": ts(60)})

    # ---- SCATTERED INDEPENDENTS ----
    scattered_tw = [
        ("@sportsfan_uk", 340), ("@watchfootball_hd", 210),
        ("@freematch_tv", 180), ("@livegoals_xyz", 420), ("@hdmatch_stream", 90),
    ]
    scattered_domains = [
        ("crickethd-live.buzz", ".buzz"), ("boxingstream-hd.icu", ".icu"),
        ("nbafree-hd.fun", ".fun"), ("ufclive-free.xyz", ".xyz"),
    ]
    scattered_invites = [
        ("https://t.me/freematch_group", "telegram"),
        ("https://discord.gg/soccerfree", "discord"),
        ("https://t.me/hdmatches_open", "telegram"),
    ]
    scattered_reddit = [
        ("u/stream_hunter99", 120), ("u/freelink_poster", 45), ("u/sportlinks_daily", 280),
    ]

    for handle, followers in scattered_tw:
        tw_id = graph.add_node({"type": "twitter_account", "label": handle,
            "metadata": {"handle": handle, "followers": followers},
            "first_seen": ts(48), "last_seen": ts(12), "source": "synthetic", "is_real_data": False})
        # Each posts one invite or promotes one domain
        if scattered_invites:
            invite = scattered_invites.pop(0) if len(scattered_invites) > 1 else scattered_invites[0]
            il_id = graph.add_node({"type": "invite_link", "label": invite[0],
                "metadata": {"url": invite[0], "platform": invite[1]},
                "first_seen": ts(40), "last_seen": ts(10), "source": "synthetic", "is_real_data": False})
            graph.add_edge({"source": tw_id, "target": il_id, "relationship": "posted", "timestamp": ts(20)})

    for label, tld in scattered_domains:
        graph.add_node({"type": "domain", "label": label,
            "metadata": {"tld": tld}, "lifecycle_stage": "setup",
            "first_seen": ts(6), "last_seen": ts(6), "source": "certstream", "is_real_data": True})

    for username, karma in scattered_reddit:
        graph.add_node({"type": "reddit_account", "label": username,
            "metadata": {"username": username, "karma": karma},
            "first_seen": ts(24), "last_seen": ts(8), "source": "synthetic", "is_real_data": False})

    graph.save()
    logger.info(f"Synthetic data generated: {len(graph.get_all_nodes())} nodes, {len(graph.get_all_edges())} edges")

    scoring.run_all_analysis(graph)
    logger.info("Analysis complete.")


if __name__ == "__main__":
    graph = GraphStore(config.GRAPH_DATA_PATH)
    graph.reset()
    generate_synthetic_data(graph)
    stats = graph.get_stats()
    print(f"\nGraph stats: {stats}")
