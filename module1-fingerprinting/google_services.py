import json
import logging

import config

log = logging.getLogger(__name__)

_gemini_client = None
_youtube_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in config.py")
        from google import genai
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


def _get_youtube():
    global _youtube_client
    if _youtube_client is None:
        if not config.YOUTUBE_API_KEY:
            raise RuntimeError("YOUTUBE_API_KEY not set in config.py")
        from googleapiclient.discovery import build
        _youtube_client = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)
    return _youtube_client


def generate_ai_analysis(match_result: dict, suspect_filename: str) -> dict:
    """
    Generate a Gemini-powered explanation and DMCA notice draft from a fusion result.
    Returns {"explanation": str, "dmca_notice": str}
    """
    from google import genai

    client = _get_gemini()
    verdict      = match_result.get("verdict", "NO_MATCH")
    score        = match_result.get("overall_score", 0)
    per_layer    = match_result.get("per_layer", {})
    matched_name = match_result.get("matched_name", "Unknown")
    agreeing     = match_result.get("agreeing_layers", 0)
    is_match     = verdict in ("MATCH", "WEAK_MATCH")

    dmca_instruction = (
        'A formal DMCA Section 512(c) takedown notice including: identification of the '
        'infringed work, description of the infringing material, good faith statement, '
        'and signature block. Use placeholders [RIGHTS HOLDER NAME], [DATE], [CONTACT EMAIL].'
        if is_match else '""'
    )

    prompt = f"""You are a sports rights protection AI analyst.

Protected video: "{matched_name}"
Suspect clip: "{suspect_filename}"
Verdict: {verdict}
Confidence: {score:.1%}
Layers agreeing: {agreeing}/3
  Visual pHash: {per_layer.get('layer1', 0):.1%}
  Audio Chromaprint: {per_layer.get('layer2', 0):.1%}
  Match DNA: {per_layer.get('layer4', 0):.1%}

Return JSON with exactly two fields:
{{
  "explanation": "2-3 sentence professional analysis of the fingerprint result. Mention which specific layers fired and what that signals technically.",
  "dmca_notice": {dmca_instruction}
}}

ONLY return the JSON object. No markdown fences, no preamble."""

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1500,
        ),
    )
    text = response.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = text.find("{")
    if start > 0:
        text = text[start:]

    result = json.loads(text)
    log.info("[Gemini] AI analysis done — verdict=%s score=%.2f", verdict, score)
    return result


def search_youtube_piracy(video_name: str) -> list[dict]:
    """
    Search YouTube for clips that may be pirating the given registered video.
    Returns a list of results sorted by suspicion score (highest first).
    """
    if not config.YOUTUBE_SEARCH_ENABLED:
        return []

    yt = _get_youtube()
    query = _build_query(video_name)

    request = yt.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=config.YOUTUBE_MAX_RESULTS,
        order="relevance",
    )
    response = request.execute()

    results = []
    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        vid_id  = item.get("id", {}).get("videoId", "")
        title   = snippet.get("title", "")
        desc    = snippet.get("description", "")
        results.append({
            "video_id":       vid_id,
            "title":          title,
            "channel":        snippet.get("channelTitle", ""),
            "published_at":   snippet.get("publishedAt", ""),
            "url":            f"https://www.youtube.com/watch?v={vid_id}",
            "thumbnail":      snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "suspicious_score": _score_suspicion(title, desc),
        })

    results.sort(key=lambda x: x["suspicious_score"], reverse=True)
    log.info("[YouTube] Scanned '%s' → %d results (query: %s)", video_name, len(results), query)
    return results


def _build_query(video_name: str) -> str:
    name   = video_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").lower()
    sports = [
        "cricket", "football", "basketball", "badminton",
        "formula1", "formula 1", "f1", "soccer", "tennis",
        "baseball", "rugby", "ufc", "boxing",
    ]
    sport = next((s for s in sports if s in name), "")
    if sport:
        return f"{sport} full match live stream free HD"
    return f"{name} live stream free watch"


def _score_suspicion(title: str, description: str) -> int:
    text     = (title + " " + description).lower()
    keywords = [
        "free", "live", "stream", "hd", "watch", "full", "match",
        "720p", "1080p", "online", "crack", "illegal", "unofficial",
    ]
    return sum(1 for kw in keywords if kw in text)
