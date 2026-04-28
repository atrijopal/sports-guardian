"""
google_services.py — Centralized Google API service layer for Module 2.
Three services: GeminiService, YouTubeService, SafeBrowsingService.
All instantiated once in app.py lifespan and reused.
"""

import json
import logging
import requests

import config

log = logging.getLogger(__name__)

_SB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
_THREAT_TYPES = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"]


# ─────────────────────────────────────────────
# Safe Browsing
# ─────────────────────────────────────────────

class SafeBrowsingService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stats = {"checked": 0, "hits": 0}

    def check_domains(self, domains: list[str]) -> dict[str, dict]:
        """
        Batch check. Returns {domain: {threat_type, google_confirmed: True}} for hits only.
        """
        if not domains or not self.api_key:
            return {}

        urls = [f"http://{d}/" for d in domains]
        payload = {
            "client": {"clientId": "sports101-piracy-monitor", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": _THREAT_TYPES,
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": u} for u in urls],
            },
        }
        try:
            resp = requests.post(_SB_URL, params={"key": self.api_key},
                                 json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            hits: dict[str, dict] = {}
            for match in data.get("matches", []):
                url = match.get("threat", {}).get("url", "")
                domain = url.replace("http://", "").replace("https://", "").rstrip("/")
                hits[domain] = {
                    "threat_type": match.get("threatType", ""),
                    "platform_type": match.get("platformType", ""),
                    "google_confirmed": True,
                }
            self.stats["checked"] += len(domains)
            self.stats["hits"] += len(hits)
            log.info("[SB] Checked %d domains — %d hits", len(domains), len(hits))
            return hits
        except Exception as e:
            log.error("[SB] API error: %s", e)
            return {}

    def check_single(self, domain: str) -> dict | None:
        hits = self.check_domains([domain])
        return hits.get(domain)


# ─────────────────────────────────────────────
# YouTube
# ─────────────────────────────────────────────

class YouTubeService:
    def __init__(self, api_key: str):
        from googleapiclient.discovery import build
        self.client = build("youtube", "v3", developerKey=api_key)
        self.stats = {"searches": 0, "channels_found": 0}

    def hunt_piracy_channels(self, queries: list[str], max_per_query: int = 5) -> list[dict]:
        """
        Run multiple search queries, deduplicate, return enriched channel list.
        """
        seen_ids: set[str] = set()
        results: list[dict] = []

        for query in queries:
            try:
                resp = self.client.search().list(
                    part="snippet", q=query, type="video",
                    maxResults=max_per_query, order="relevance",
                ).execute()
                self.stats["searches"] += 1

                for item in resp.get("items", []):
                    vid_id = item.get("id", {}).get("videoId", "")
                    if not vid_id or vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)
                    snippet = item.get("snippet", {})
                    channel_id = snippet.get("channelId", "")
                    title = snippet.get("title", "")
                    channel_title = snippet.get("channelTitle", "")
                    published = snippet.get("publishedAt", "")
                    thumb = snippet.get("thumbnails", {}).get("medium", {}).get("url", "")

                    results.append({
                        "video_id":       vid_id,
                        "channel_id":     channel_id,
                        "title":          title,
                        "channel":        channel_title,
                        "published_at":   published,
                        "url":            f"https://www.youtube.com/watch?v={vid_id}",
                        "channel_url":    f"https://www.youtube.com/channel/{channel_id}",
                        "thumbnail":      thumb,
                        "query":          query,
                        "suspicious_score": self._score(title, ""),
                    })
            except Exception as e:
                log.error("[YT] Search failed for '%s': %s", query, e)

        results.sort(key=lambda x: x["suspicious_score"], reverse=True)
        self.stats["channels_found"] = len(results)
        log.info("[YT] Hunt complete — %d results from %d queries", len(results), len(queries))
        return results

    def search_for_domain(self, domain: str) -> list[dict]:
        name = domain.rsplit(".", 1)[0]
        return self.hunt_piracy_channels([f"{name} live stream", f"{name} sports"], max_per_query=3)

    @staticmethod
    def _score(title: str, desc: str) -> int:
        text = (title + " " + desc).lower()
        kws = ["free", "live", "stream", "hd", "watch", "full", "match",
               "720p", "1080p", "online", "crack", "illegal"]
        return sum(1 for k in kws if k in text)


# ─────────────────────────────────────────────
# Gemini
# ─────────────────────────────────────────────

_OLLAMA_URL  = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "llama3.1:8b"


def _call_ollama(prompt: str, max_tokens: int = 1500) -> str:
    resp = requests.post(_OLLAMA_URL, json={
        "model": _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3},
    }, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


class GeminiService:
    def __init__(self, api_key: str, model: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.stats = {"briefings": 0, "profiles": 0, "errors": 0, "ollama_fallbacks": 0}

    def _call(self, prompt: str, max_tokens: int = 1500) -> str:
        # Try Gemini first
        try:
            from google import genai
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text.strip()
        except Exception as e:
            log.warning("[Gemini] Failed (%s) — falling back to Ollama %s", e, _OLLAMA_MODEL)
            self.stats["errors"] += 1
            self.stats["ollama_fallbacks"] += 1
            return _call_ollama(prompt, max_tokens)

    def generate_briefing(self, stats: dict, top_threats: list[dict]) -> dict:
        """
        Generate a structured threat intelligence briefing from graph state.
        Returns {"threat_level", "summary", "top_threats", "clusters", "recommended_actions", "timestamp"}
        """
        threats_text = "\n".join([
            f"- {t.get('label','?')} (score:{t.get('threat_score',0):.0f}, "
            f"type:{t.get('type','?')}, "
            f"google_confirmed:{t.get('metadata',{}).get('google_confirmed',False)})"
            for t in top_threats[:10]
        ])

        prompt = f"""You are a sports rights protection threat intelligence analyst.

Current graph statistics:
- Total nodes: {stats.get('total_nodes', 0)}
- Total edges: {stats.get('total_edges', 0)}
- Domain nodes: {stats.get('nodes_by_type', {}).get('domain', 0)}
- YouTube channels tracked: {stats.get('nodes_by_type', {}).get('youtube_channel', 0)}
- Operator clusters: {stats.get('clusters', 0)}
- Threats flagged today: {stats.get('flagged_today', 0)}
- Safe Browsing confirmed: {stats.get('sb_confirmed', 0)}

Top threat entities:
{threats_text if threats_text else "No threats detected yet."}

Generate a threat intelligence briefing. Return JSON only:
{{
  "threat_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "summary": "2-3 sentence executive summary of current piracy threat landscape",
  "top_threats": ["domain1 — reason", "domain2 — reason"],
  "cluster_analysis": "1-2 sentences about operator clustering patterns",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "sports_at_risk": ["Football", "Cricket", "NBA"]
}}

Return ONLY the JSON object."""

        try:
            text = self._call(prompt)
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(text)
            self.stats["briefings"] += 1
            log.info("[Gemini] Briefing generated — threat level: %s", result.get("threat_level"))
            return result
        except Exception as e:
            self.stats["errors"] += 1
            log.error("[Gemini] Briefing failed: %s", e)
            return {
                "threat_level": "UNKNOWN",
                "summary": f"Briefing generation failed: {e}",
                "top_threats": [],
                "cluster_analysis": "",
                "recommended_actions": [],
                "sports_at_risk": [],
            }

    def generate_operator_profile(self, node: dict, neighbors: list[dict], edge_count: int) -> str:
        """
        Generate a natural-language operator profile for a specific graph node.
        """
        meta = node.get("metadata", {})
        neighbors_text = ", ".join([n.get("label", "?") for n in neighbors[:8]])
        sb_status = "Google-confirmed threat" if meta.get("google_confirmed") else "not Google-confirmed"
        tier2_risk = meta.get("tier2_risk", "unknown")

        prompt = f"""You are a sports rights protection threat intelligence analyst. Write a concise operator profile.

Entity: {node.get('label', 'Unknown')}
Type: {node.get('type', 'unknown')}
Threat score: {node.get('threat_score', 0):.0f}/100
Lifecycle stage: {node.get('lifecycle_stage', 'unknown')}
Safe Browsing status: {sb_status}
Gemini NLP risk: {tier2_risk}
First seen: {node.get('first_seen', 'unknown')}
Connections: {edge_count} edges to: {neighbors_text or 'none'}
Tier2 reasons: {', '.join(meta.get('tier2_reasons', []))}

Write a 3-4 sentence intelligence profile: what this entity likely is, what sports rights it threatens, how it operates, and what action should be taken. Be specific and analytical."""

        try:
            result = self._call(prompt, max_tokens=400)
            self.stats["profiles"] += 1
            return result
        except Exception as e:
            self.stats["errors"] += 1
            log.error("[Gemini] Profile failed: %s", e)
            return f"Profile generation unavailable: {e}"
