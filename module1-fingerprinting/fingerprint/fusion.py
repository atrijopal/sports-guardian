# fingerprint/fusion.py — Combine layer scores into a final match decision.

import logging
import config
from fingerprint import layer1_visual, layer2_audio, layer4_dna

log = logging.getLogger(__name__)

# Per-layer agreement thresholds (independent of the overall threshold)
_L1_AGREE = 0.35
_L2_AGREE = 0.50
_L4_AGREE = 0.60


def fuse(layer1_score: float, layer2_score: float, layer4_score: float) -> dict:
    """
    Weighted average of layer scores + minimum agreeing layers check.
    Returns full result dict with verdict, explanation, and per-layer breakdown.
    """
    weights = config.FUSION_WEIGHTS
    overall = (
        weights["layer1"] * layer1_score
        + weights["layer2"] * layer2_score
        + weights["layer4"] * layer4_score
    )
    overall = round(overall, 4)

    # Count agreeing layers
    agreed = []
    failed = []

    if layer1_score >= _L1_AGREE:
        agreed.append("visual")
    else:
        failed.append(("visual", layer1_score))

    if layer2_score >= _L2_AGREE:
        agreed.append("audio")
    else:
        failed.append(("audio", layer2_score))

    if layer4_score >= _L4_AGREE:
        agreed.append("DNA")
    else:
        failed.append(("DNA", layer4_score))

    agreeing_layers = len(agreed)
    is_match = (
        overall >= config.FUSION_MATCH_THRESHOLD
        and agreeing_layers >= config.FUSION_MIN_AGREEING_LAYERS
    )

    # Verdict string
    if is_match:
        verdict = "MATCH"
    elif overall >= config.FUSION_MATCH_THRESHOLD * 0.75:
        verdict = "WEAK_MATCH"
    else:
        verdict = "NO_MATCH"

    # Human-readable explanation
    explanation = _build_explanation(agreed, failed, verdict)

    return {
        "overall_score": overall,
        "is_match": is_match,
        "agreeing_layers": agreeing_layers,
        "per_layer": {
            "layer1": round(layer1_score, 4),
            "layer2": round(layer2_score, 4),
            "layer4": round(layer4_score, 4),
        },
        "verdict": verdict,
        "explanation": explanation,
    }


def _build_explanation(agreed: list[str], failed: list[tuple], verdict: str) -> str:
    parts = []
    if agreed:
        parts.append(f"Matched on {' + '.join(agreed)}.")
    for name, score in failed:
        if name == "audio" and score == 0.0:
            parts.append("Audio was stripped or muted.")
        elif name == "DNA" and score == 0.0:
            parts.append("DNA match weak (clip may be too short or heavily altered).")
        elif score == 0.0:
            parts.append(f"{name.capitalize()} layer found no match.")
        else:
            parts.append(f"{name.capitalize()} match was weak ({int(score*100)}%).")
    if verdict == "WEAK_MATCH":
        parts.append("Overall confidence is marginal.")
    return " ".join(parts)


def best_match(suspect_fp: dict, all_originals: list[dict]) -> dict:
    """
    Score suspect against every registered original.
    Return the result with the highest overall score, or a NO_MATCH result
    if nothing clears the threshold.
    """
    best_result = None
    best_score = -1.0
    best_meta = None

    for original in all_originals:
        s1 = layer1_visual.match_fingerprints(suspect_fp["layer1"], original["layer1"])
        s2 = layer2_audio.match_fingerprints(suspect_fp["layer2"], original["layer2"])
        s4 = layer4_dna.match_fingerprints(suspect_fp["layer4"], original["layer4"])

        log.info(
            "Comparing against '%s': L1=%.2f L2=%.2f L4=%.2f",
            original.get("name"), s1, s2, s4,
        )

        result = fuse(s1, s2, s4)
        if result["overall_score"] > best_score:
            best_score = result["overall_score"]
            best_result = result
            best_meta = original

    if best_result is None:
        return {
            "is_match": False,
            "verdict": "NO_MATCH",
            "overall_score": 0.0,
            "explanation": "No registered videos to compare against.",
            "per_layer": {"layer1": 0.0, "layer2": 0.0, "layer4": 0.0},
        }

    best_result["matched_video_id"] = best_meta.get("video_id")
    best_result["matched_name"] = best_meta.get("name")
    best_result["matched_registered_at"] = best_meta.get("registered_at")
    return best_result
