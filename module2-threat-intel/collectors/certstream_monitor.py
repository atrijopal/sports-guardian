import threading
import queue
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from rapidfuzz import fuzz
import config

logger = logging.getLogger(__name__)

_scored_recently: dict[str, float] = {}
_DEDUP_WINDOW_SEC = 60
_sb_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sb-rt")


def _get_registrable(domain: str) -> str:
    domain = domain.lower().lstrip("*.")
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


class CertstreamMonitor:
    def __init__(self, graph, notify_callback=None):
        self.graph = graph
        self.notify_callback = notify_callback
        self.running = False
        self._thread: threading.Thread | None = None
        self._sb_service = None  # injected by app.py after init

        self.feed_queue: queue.Queue = queue.Queue(maxsize=200)
        self.tier2_queue: queue.Queue = queue.Queue()
        self.notify_queue: queue.Queue = queue.Queue()

        self.stats = {
            "certificates_seen": 0,
            "domains_scored": 0,
            "domains_flagged": 0,
            "sb_realtime_hits": 0,
        }

    def inject_sb_service(self, sb_service):
        self._sb_service = sb_service

    def score_domain(self, domain: str) -> dict:
        domain = domain.lower()
        name = domain.rsplit(".", 1)[0] if "." in domain else domain
        tld  = "." + domain.rsplit(".", 1)[-1] if "." in domain else ""

        score = 0
        reasons = []

        kw_hits = 0
        for kw in config.CERT_KEYWORDS:
            if kw in domain:
                if kw_hits < 2:
                    score += config.CERT_SCORE_KEYWORD
                    reasons.append(f"keyword:{kw}")
                kw_hits += 1

        if tld in config.CERT_CHEAP_TLDS:
            score += config.CERT_SCORE_CHEAP_TLD
            reasons.append(f"cheap_tld:{tld}")

        for brand in config.CERT_KNOWN_BRANDS:
            ratio = fuzz.partial_ratio(brand, name)
            if ratio > 70:
                score += config.CERT_SCORE_BRAND_SIMILARITY
                reasons.append(f"brand_match:{brand}({ratio}%)")
                break

        if len(name) > 20:
            score += config.CERT_SCORE_LONG_DOMAIN
            reasons.append(f"long_domain:{len(name)}c")

        return {
            "domain": domain,
            "score": score,
            "reasons": reasons,
            "flagged": score >= config.CERT_TIER1_FLAG_THRESHOLD,
        }

    def _check_sb_async(self, domain: str, feed_item: dict):
        """Run Safe Browsing check in thread pool, update feed_item and push alert if hit."""
        if not self._sb_service:
            return
        try:
            hit = self._sb_service.check_single(domain)
            if hit:
                self.stats["sb_realtime_hits"] += 1
                feed_item["sb_status"] = "THREAT"
                feed_item["sb_threat_type"] = hit.get("threat_type", "")
                feed_item["google_confirmed"] = True
                self.notify_queue.put({
                    **feed_item,
                    "_alert_type": "sb_realtime_hit",
                    "threat_score": 100,
                })
                logger.warning("[SB-RT] *** CONFIRMED THREAT: %s (%s) ***", domain, hit.get("threat_type"))
            else:
                feed_item["sb_status"] = "clean"
        except Exception as e:
            logger.error("[SB-RT] Error checking %s: %s", domain, e)
            feed_item["sb_status"] = "error"

    def _on_cert_message(self, message, context):
        if message.get("message_type") != "certificate_update":
            return

        try:
            domains = message["data"]["leaf_cert"]["all_domains"]
        except (KeyError, TypeError):
            return

        self.stats["certificates_seen"] += 1
        import time
        now = time.time()
        seen_registrable: set[str] = set()

        for raw_domain in domains:
            if "*" in raw_domain:
                continue
            registrable = _get_registrable(raw_domain)
            if registrable in seen_registrable:
                continue
            last_scored = _scored_recently.get(registrable, 0)
            if now - last_scored < _DEDUP_WINDOW_SEC:
                continue

            _scored_recently[registrable] = now
            seen_registrable.add(registrable)

            result = self.score_domain(registrable)
            self.stats["domains_scored"] += 1

            feed_item = {
                "domain":       registrable,
                "tier1_score":  result["score"],
                "flagged":      result["flagged"],
                "reasons":      result["reasons"],
                "sb_status":    "checking" if result["flagged"] else "skipped",
                "google_confirmed": False,
                "ts":           datetime.now(timezone.utc).isoformat(),
            }

            try:
                self.feed_queue.put_nowait(feed_item)
            except queue.Full:
                try:
                    self.feed_queue.get_nowait()
                    self.feed_queue.put_nowait(feed_item)
                except Exception:
                    pass

            if result["flagged"]:
                self.stats["domains_flagged"] += 1
                self.tier2_queue.put({
                    "domain":        registrable,
                    "tier1_score":   result["score"],
                    "tier1_reasons": result["reasons"],
                })
                # Fire-and-forget Safe Browsing check in thread pool
                _sb_executor.submit(self._check_sb_async, registrable, feed_item)

    async def enrich_domain(self, domain: str, node_id: str):
        try:
            import dns.resolver, asyncio
            resolver = dns.resolver.Resolver()
            resolver.timeout = 3
            answers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: resolver.resolve(domain, "A"))
            ip = str(answers[0]) if answers else None
            node = self.graph.get_node(node_id)
            if node and ip:
                node["metadata"]["ip"] = ip
                node["metadata"]["is_live"] = True
                self.graph.save()
        except Exception:
            pass

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("CertstreamMonitor started")

    def _run(self):
        try:
            import certstream
            certstream.listen_for_events(self._on_cert_message,
                                         url="wss://certstream.calidog.io/")
        except Exception as e:
            logger.error(f"Certstream error: {e}")
            self.running = False

    def stop(self):
        self.running = False

    def get_stats(self) -> dict:
        return dict(self.stats)
