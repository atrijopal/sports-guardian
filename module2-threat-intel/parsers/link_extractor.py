import re
from urllib.parse import urlparse

INVITE_PATTERNS = [
    (r'(https?://t\.me/[\w+]+)', 'telegram'),
    (r'(https?://telegram\.me/[\w+]+)', 'telegram'),
    (r'(https?://discord\.gg/[\w]+)', 'discord'),
    (r'(https?://discord\.com/invite/[\w]+)', 'discord'),
    (r'(https?://chat\.whatsapp\.com/[\w]+)', 'whatsapp'),
]

URL_PATTERN = re.compile(r'(https?://[^\s<>"\']+)')

STREAM_KEYWORDS = ["stream", "live", "watch", "free", "hd", "match",
                   "sport", "football", "soccer", "cricket", "m3u8"]

CHEAP_TLDS = {".xyz", ".top", ".site", ".online", ".live",
              ".stream", ".club", ".fun", ".icu", ".buzz"}


def extract_invite_links(text: str) -> list[dict]:
    results = []
    seen = set()
    for pattern, platform in INVITE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            url = match.group(1)
            if url in seen:
                continue
            seen.add(url)
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            group_id = path_parts[-1] if path_parts else ""
            results.append({"url": url, "platform": platform, "group_id": group_id})
    return results


def extract_domains(text: str) -> list[dict]:
    results = []
    seen = set()
    for match in URL_PATTERN.finditer(text):
        url = match.group(1).rstrip(".,;:)")
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if not domain or domain in seen:
                continue
            # skip known social platforms
            if any(x in domain for x in ["twitter.com", "reddit.com", "t.me", "discord", "whatsapp", "youtube", "facebook", "instagram"]):
                continue
            seen.add(domain)
            tld = "." + domain.rsplit(".", 1)[-1] if "." in domain else ""
            domain_lower = domain.replace("www.", "")
            matched_kw = [kw for kw in STREAM_KEYWORDS if kw in domain_lower]
            is_suspicious = bool(matched_kw) or tld in CHEAP_TLDS
            if is_suspicious:
                results.append({
                    "url": url,
                    "domain": domain_lower,
                    "tld": tld,
                    "is_suspicious": True,
                    "matched_keywords": matched_kw,
                })
        except Exception:
            continue
    return results


def extract_all(text: str) -> dict:
    raw_urls = [m.group(1) for m in URL_PATTERN.finditer(text)]
    return {
        "invite_links": extract_invite_links(text),
        "domains": extract_domains(text),
        "raw_urls": raw_urls,
    }
