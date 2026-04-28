import logging

import requests

import config

log = logging.getLogger(__name__)

_SB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

_THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]


def check_domains(domains: list[str]) -> dict[str, dict]:
    """
    Batch-check domains against Google Safe Browsing API v4.

    Returns a dict of {domain: {threat_type, platform_type, google_confirmed: True}}
    for every domain that has a confirmed hit. Clean domains are absent from the result.
    """
    if not getattr(config, "SAFE_BROWSING_ENABLED", False):
        return {}
    if not getattr(config, "SAFE_BROWSING_API_KEY", ""):
        return {}
    if not domains:
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

    resp = requests.post(
        _SB_URL,
        params={"key": config.SAFE_BROWSING_API_KEY},
        json=payload,
        timeout=10,
    )
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

    log.info("[SafeBrowsing] Checked %d domains — %d confirmed hits", len(domains), len(hits))
    return hits
