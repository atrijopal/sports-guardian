import logging
import math
from datetime import datetime, timezone, timedelta
from rapidfuzz import fuzz
import config

logger = logging.getLogger(__name__)


def _parse_dt(s: str) -> datetime:
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def compute_threat_scores(graph) -> None:
    nodes = graph.get_all_nodes()
    if not nodes:
        return

    edge_counts: dict[str, int] = {}
    for e in graph.get_all_edges():
        edge_counts[e["source"]] = edge_counts.get(e["source"], 0) + 1
        edge_counts[e["target"]] = edge_counts.get(e["target"], 0) + 1

    max_edges = max(edge_counts.values(), default=1)
    now = datetime.now(timezone.utc)

    for node in nodes:
        nid = node["id"]
        conn_count = edge_counts.get(nid, 0)
        conn_norm = conn_count / max_edges

        last_seen = _parse_dt(node.get("last_seen", now.isoformat()))
        hours_ago = max(0, (now - last_seen).total_seconds() / 3600)
        recency = math.exp(-hours_ago / 48)

        type_weight = config.THREAT_TYPE_WEIGHTS.get(node.get("type", ""), 0.3)

        raw = (
            config.THREAT_WEIGHT_CONNECTIONS * conn_norm +
            config.THREAT_WEIGHT_RECENCY * recency +
            config.THREAT_WEIGHT_TYPE * type_weight
        )
        node["threat_score"] = round(min(100.0, raw * 100), 1)

    graph.save()
    logger.info(f"Computed threat scores for {len(nodes)} nodes")


def _union_find_root(parent: dict, x: str) -> str:
    while parent.get(x, x) != x:
        parent[x] = parent.get(parent.get(x, x), x)
        x = parent[x]
    return x


def _union_find_merge(parent: dict, a: str, b: str):
    ra, rb = _union_find_root(parent, a), _union_find_root(parent, b)
    if ra != rb:
        parent[rb] = ra


def detect_clusters(graph) -> None:
    domains = graph.get_nodes_by_type("domain")
    if len(domains) < 2:
        return

    parent: dict[str, str] = {d["id"]: d["id"] for d in domains}

    node_neighbors: dict[str, set] = {}
    for d in domains:
        neighbors = set(n["id"] for n in graph.get_neighbors(d["id"]))
        node_neighbors[d["id"]] = neighbors

    for i, da in enumerate(domains):
        for db in domains[i+1:]:
            score = 0
            tld_a = da.get("metadata", {}).get("tld", "")
            tld_b = db.get("metadata", {}).get("tld", "")
            if tld_a and tld_a == tld_b:
                score += 1

            ts_a = _parse_dt(da.get("first_seen", ""))
            ts_b = _parse_dt(db.get("first_seen", ""))
            if abs((ts_a - ts_b).total_seconds()) < config.CLUSTER_SAME_TLD_WINDOW_HOURS * 3600:
                score += 2

            label_a = da.get("label", "").rsplit(".", 1)[0]
            label_b = db.get("label", "").rsplit(".", 1)[0]
            if fuzz.partial_ratio(label_a, label_b) > config.CLUSTER_BRAND_SIMILARITY_THRESHOLD:
                score += 2

            shared = node_neighbors[da["id"]] & node_neighbors[db["id"]]
            if len(shared) >= config.CLUSTER_SHARED_CHANNEL_THRESHOLD:
                score += 3

            ip_a = da.get("metadata", {}).get("ip", "")
            ip_b = db.get("metadata", {}).get("ip", "")
            if ip_a and ip_a == ip_b:
                score += 3

            if score >= 4:
                _union_find_merge(parent, da["id"], db["id"])

    cluster_map: dict[str, str] = {}
    counter = 1
    for d in domains:
        root = _union_find_root(parent, d["id"])
        if root not in cluster_map:
            cluster_map[root] = f"cluster_{counter}"
            counter += 1

    cluster_members: dict[str, set] = {}
    for d in domains:
        root = _union_find_root(parent, d["id"])
        cid = cluster_map[root]
        d["cluster_id"] = cid
        cluster_members.setdefault(cid, set()).add(d["id"])

        for nb in graph.get_neighbors(d["id"]):
            nb["cluster_id"] = cid

    for cid, member_ids in cluster_members.items():
        members = list(member_ids)
        for i in range(len(members)):
            for j in range(i+1, len(members)):
                graph.add_edge({
                    "source": members[i],
                    "target": members[j],
                    "relationship": "same_operator",
                })

    # Reset singleton cluster_ids
    for d in domains:
        root = _union_find_root(parent, d["id"])
        cid = cluster_map[root]
        members = cluster_members.get(cid, set())
        if len(members) <= 1:
            d["cluster_id"] = None

    graph.save()
    logger.info("Cluster detection complete")


def assign_lifecycle_stages(graph) -> None:
    now = datetime.now(timezone.utc)
    dormant_cutoff = now - timedelta(hours=48)

    for node in graph.get_nodes_by_type("domain"):
        edges = graph.get_edges_for_node(node["id"])
        promo_sources = {"twitter_account", "reddit_account", "telegram_channel", "invite_link"}

        promo_edges = [
            e for e in edges
            if e.get("relationship") in ("posted", "promotes", "links_to", "shared_in")
        ]

        promoting_types = set()
        for e in promo_edges:
            other_id = e["target"] if e["source"] == node["id"] else e["source"]
            other = graph.get_node(other_id)
            if other and other.get("type") in promo_sources:
                promoting_types.add(other.get("type"))

        last_seen = _parse_dt(node.get("last_seen", now.isoformat()))
        is_old = last_seen < dormant_cutoff

        if is_old and node.get("lifecycle_stage") in ("active", "promotion"):
            node["lifecycle_stage"] = "dormant"
        elif len(promo_edges) >= 3 or len(promoting_types) >= 2:
            node["lifecycle_stage"] = "active"
        elif len(promo_edges) > 0:
            node["lifecycle_stage"] = "promotion"
        else:
            node["lifecycle_stage"] = "setup"

    graph.save()
    logger.info("Lifecycle stages assigned")


def compute_velocity(graph, node_id: str, window_hours: int = 24) -> float:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    edges = graph.get_edges_for_node(node_id)
    recent = sum(1 for e in edges if _parse_dt(e.get("timestamp", "")) > cutoff)
    return round(recent / window_hours, 3)


def run_all_analysis(graph) -> None:
    import time
    for fn in (compute_threat_scores, detect_clusters, assign_lifecycle_stages):
        t0 = time.time()
        fn(graph)
        logger.info(f"{fn.__name__} took {time.time()-t0:.2f}s")
