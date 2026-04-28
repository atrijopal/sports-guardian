import json
import os
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class GraphStore:
    def __init__(self, persist_path: str):
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.persist_path = persist_path
        self._label_index: dict[tuple, str] = {}  # (type, label) -> id
        os.makedirs(os.path.dirname(persist_path) if os.path.dirname(persist_path) else ".", exist_ok=True)
        self.load()

    def add_node(self, node: dict) -> str:
        node_type = node.get("type", "")
        label = node.get("label", "")
        key = (node_type, label)

        if key in self._label_index:
            existing_id = self._label_index[key]
            existing = self.nodes[existing_id]
            existing["last_seen"] = node.get("last_seen", datetime.now(timezone.utc).isoformat())
            existing_meta = existing.get("metadata", {})
            existing_meta.update(node.get("metadata", {}))
            existing["metadata"] = existing_meta
            if node.get("threat_score", 0) > existing.get("threat_score", 0):
                existing["threat_score"] = node["threat_score"]
            return existing_id

        node_id = node.get("id") or str(uuid.uuid4())
        node["id"] = node_id
        if "threat_score" not in node:
            node["threat_score"] = 0.0
        if "lifecycle_stage" not in node:
            node["lifecycle_stage"] = "setup"
        if "cluster_id" not in node:
            node["cluster_id"] = None
        if "first_seen" not in node:
            node["first_seen"] = datetime.now(timezone.utc).isoformat()
        if "last_seen" not in node:
            node["last_seen"] = node["first_seen"]

        self.nodes[node_id] = node
        self._label_index[key] = node_id
        return node_id

    def add_edge(self, edge: dict) -> str:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        rel = edge.get("relationship", "")
        sig = (src, tgt, rel)

        for existing in self.edges.values():
            if (existing["source"], existing["target"], existing["relationship"]) == sig:
                existing["timestamp"] = edge.get("timestamp", datetime.now(timezone.utc).isoformat())
                return existing["id"]

        edge_id = edge.get("id") or str(uuid.uuid4())
        edge["id"] = edge_id
        if "timestamp" not in edge:
            edge["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "metadata" not in edge:
            edge["metadata"] = {}
        self.edges[edge_id] = edge
        return edge_id

    def get_node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def get_edges_for_node(self, node_id: str) -> list[dict]:
        return [e for e in self.edges.values()
                if e["source"] == node_id or e["target"] == node_id]

    def get_neighbors(self, node_id: str) -> list[dict]:
        neighbors = []
        for e in self.get_edges_for_node(node_id):
            other_id = e["target"] if e["source"] == node_id else e["source"]
            n = self.nodes.get(other_id)
            if n:
                neighbors.append(n)
        return neighbors

    def get_all_nodes(self) -> list[dict]:
        return list(self.nodes.values())

    def get_all_edges(self) -> list[dict]:
        return list(self.edges.values())

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        return [n for n in self.nodes.values() if n.get("type") == node_type]

    def get_nodes_by_cluster(self, cluster_id: str) -> list[dict]:
        return [n for n in self.nodes.values() if n.get("cluster_id") == cluster_id]

    def find_node(self, node_type: str, label: str) -> dict | None:
        key = (node_type, label)
        node_id = self._label_index.get(key)
        return self.nodes.get(node_id) if node_id else None

    def get_stats(self) -> dict:
        nodes_by_type: dict[str, int] = {}
        for n in self.nodes.values():
            t = n.get("type", "unknown")
            nodes_by_type[t] = nodes_by_type.get(t, 0) + 1

        clusters = set(n["cluster_id"] for n in self.nodes.values() if n.get("cluster_id"))

        today = datetime.now(timezone.utc).date().isoformat()
        flagged_today = sum(
            1 for n in self.nodes.values()
            if n.get("last_seen", "")[:10] == today and n.get("threat_score", 0) >= 50
        )

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": nodes_by_type,
            "clusters": len(clusters),
            "flagged_today": flagged_today,
        }

    def save(self):
        data = {"nodes": list(self.nodes.values()), "edges": list(self.edges.values())}
        dir_name = os.path.dirname(self.persist_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            shutil.move(tmp_path, self.persist_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def load(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nodes = {}
            self.edges = {}
            self._label_index = {}
            for n in data.get("nodes", []):
                self.nodes[n["id"]] = n
                self._label_index[(n.get("type", ""), n.get("label", ""))] = n["id"]
            for e in data.get("edges", []):
                self.edges[e["id"]] = e
            logger.info(f"Loaded graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")

    def reset(self):
        self.nodes = {}
        self.edges = {}
        self._label_index = {}
        if os.path.exists(self.persist_path):
            os.unlink(self.persist_path)
