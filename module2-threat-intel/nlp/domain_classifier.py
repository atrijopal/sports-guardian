import queue
import logging
from datetime import datetime, timezone
import config
from nlp.classifier import classify_domains

logger = logging.getLogger(__name__)


class DomainClassifierQueue:
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self.results: list[dict] = []
        self.stats = {
            "domains_queued": 0,
            "domains_classified": 0,
            "domains_flagged_tier2": 0,
        }

    def enqueue(self, domain: str, tier1_score: int, tier1_reasons: list[str]):
        try:
            self._queue.put_nowait({
                "domain": domain,
                "tier1_score": tier1_score,
                "tier1_reasons": tier1_reasons,
            })
            self.stats["domains_queued"] += 1
        except queue.Full:
            pass

    async def process_batch(self, graph, notify_callback=None):
        batch = []
        while len(batch) < config.CERT_TIER2_MAX_BATCH:
            try:
                item = self._queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break

        if not batch:
            return

        domain_names = [item["domain"] for item in batch]
        try:
            classifications = classify_domains(domain_names)
        except Exception as e:
            logger.error(f"[Tier2] classify_domains failed: {e}")
            return

        self.stats["domains_classified"] += len(batch)

        cls_map: dict[int, dict] = {}
        for cls in classifications:
            idx = cls.get("domain_index", -1)
            if 0 <= idx < len(batch):
                cls_map[idx] = cls

        now = datetime.now(timezone.utc).isoformat()

        for i, item in enumerate(batch):
            cls = cls_map.get(i, {})
            is_suspicious = cls.get("is_suspicious", False)
            risk = cls.get("risk_level", "none")

            if not is_suspicious or risk == "none":
                continue

            self.stats["domains_flagged_tier2"] += 1

            node_id = graph.add_node({
                "type": "domain",
                "label": item["domain"],
                "metadata": {
                    "tier1_score": item["tier1_score"],
                    "tier1_reasons": item["tier1_reasons"],
                    "tier2_risk": risk,
                    "tier2_reasons": cls.get("reasons", []),
                    "tier2_decoded_name": cls.get("decoded_name", ""),
                    "tier2_confidence": cls.get("confidence", 0.0),
                    "similar_to_brands": cls.get("similar_to_brands", []),
                    "nlp_threat_level": risk,
                },
                "first_seen": now,
                "last_seen": now,
                "source": "certstream",
                "is_real_data": True,
                "lifecycle_stage": "setup",
            })
            graph.save()

            result = {
                "node_id": node_id,
                "domain": item["domain"],
                "tier1_score": item["tier1_score"],
                "tier2_risk": risk,
                "tier2_reasons": cls.get("reasons", []),
                "tier2_decoded_name": cls.get("decoded_name", ""),
                "tier2_confidence": cls.get("confidence", 0.0),
                "similar_to_brands": cls.get("similar_to_brands", []),
            }
            self.results.append(result)

            if notify_callback:
                try:
                    node_data = graph.get_node(node_id) or {}
                    node_data["_alert_type"] = "tier2_flagged"
                    await notify_callback(node_data)
                except Exception as e:
                    logger.error(f"[Tier2] notify_callback failed: {e}")
