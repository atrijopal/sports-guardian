import logging

import config
from session_registry import SessionRegistry
from watermark import layer1_visual, layer2_audio, layer3_dct

logger = logging.getLogger(__name__)


def extract_full(video_path: str, registry: SessionRegistry) -> dict:
    # Run all 3 extractors
    logger.info(f"[Extractor] Starting extraction: {video_path}")
    try:
        l1 = layer1_visual.extract_video(video_path)
    except Exception as e:
        logger.error(f"[Extractor] Layer1 error: {e}")
        l1 = {"confidence": 0.0, "session_id_int": None, "session_id_hex": None, "status": "failed"}

    try:
        l2 = layer2_audio.extract_video(video_path)
    except Exception as e:
        logger.error(f"[Extractor] Layer2 error: {e}")
        l2 = {"confidence": 0.0, "session_id_int": None, "session_id_hex": None, "status": "failed"}

    try:
        l3 = layer3_dct.extract_video(video_path)
    except Exception as e:
        logger.error(f"[Extractor] Layer3 error: {e}")
        l3 = {"confidence": 0.0, "session_id_int": None, "session_id_hex": None, "status": "failed"}

    layer_results = {
        "layer1": {"result": l1, "name": "Visual (Spread Spectrum)"},
        "layer2": {"result": l2, "name": "Audio (BPSK)"},
        "layer3": {"result": l3, "name": "DCT Structural"},
    }

    # Build votes: session_id_hex -> {count, layers, confidences, session_entry}
    votes = {}
    per_layer_out = {}

    for layer_key, lr in layer_results.items():
        res = lr["result"]
        sid_int = res.get("session_id_int")
        sid_hex = res.get("session_id_hex")
        confidence = res.get("confidence", 0.0)
        status = res.get("status", "ok")

        # Check for no_audio
        if status == "no_audio":
            per_layer_out[layer_key] = {
                "session_id_hex": None,
                "confidence": 0.0,
                "status": "no_audio",
            }
            continue

        # Validate against registry
        found = None
        if sid_int is not None:
            found = registry.lookup_by_int(sid_int)

        if found is not None and confidence >= config.LAYER_AGREEMENT_THRESHOLDS.get(layer_key, 0.3):
            hex_key = found["session_id_hex"]
            if hex_key not in votes:
                votes[hex_key] = {"count": 0, "layers": [], "confidences": [], "session": found}
            votes[hex_key]["count"] += 1
            votes[hex_key]["layers"].append(layer_key)
            votes[hex_key]["confidences"].append(confidence)
            per_layer_out[layer_key] = {
                "session_id_hex": hex_key,
                "confidence": confidence,
                "status": "match",
            }
        else:
            per_layer_out[layer_key] = {
                "session_id_hex": sid_hex,
                "confidence": confidence,
                "status": "no_match" if sid_int is not None else "uncertain",
            }

    # Pick winner
    if not votes:
        explanation = _build_explanation(per_layer_out, None, 0, "NOT ATTRIBUTED")
        return {
            "verdict": "NOT ATTRIBUTED",
            "session_id_hex": None,
            "viewer_name": None,
            "session_details": None,
            "overall_confidence": 0.0,
            "agreeing_layers": 0,
            "per_layer": per_layer_out,
            "explanation": explanation,
        }

    winner_hex = max(votes, key=lambda k: (votes[k]["count"], sum(votes[k]["confidences"])))
    winner = votes[winner_hex]
    agreeing_count = winner["count"]
    overall_confidence = sum(winner["confidences"]) / len(winner["confidences"])
    session_entry = winner["session"]

    if (agreeing_count >= config.FUSION_MIN_AGREEING_LAYERS
            and overall_confidence >= config.FUSION_OVERALL_THRESHOLD):
        verdict = "ATTRIBUTED"
    elif agreeing_count >= 1:
        verdict = "PARTIAL"
    else:
        verdict = "NOT ATTRIBUTED"

    explanation = _build_explanation(per_layer_out, session_entry, agreeing_count, verdict)

    return {
        "verdict": verdict,
        "session_id_hex": winner_hex,
        "viewer_name": session_entry["viewer_name"],
        "session_details": session_entry,
        "overall_confidence": round(overall_confidence, 3),
        "agreeing_layers": agreeing_count,
        "per_layer": per_layer_out,
        "explanation": explanation,
    }


def _build_explanation(per_layer: dict, session: dict, agreeing: int, verdict: str) -> str:
    parts = []
    viewer_str = f"{session['viewer_name']}" if session else "unknown viewer"

    status_descriptions = {
        "match": "matched",
        "no_match": "uncertain — ID not in registry",
        "no_audio": "skipped — audio track removed",
        "uncertain": "uncertain — weak signal",
        "failed": "failed — extraction error",
    }

    for layer_key, data in per_layer.items():
        layer_names = {"layer1": "Layer 1 (Visual)", "layer2": "Layer 2 (Audio)", "layer3": "Layer 3 (DCT)"}
        name = layer_names.get(layer_key, layer_key)
        status = data.get("status", "unknown")
        conf = data.get("confidence", 0.0)
        desc = status_descriptions.get(status, status)
        if status == "match":
            parts.append(f"{name}: matched {viewer_str} [{conf*100:.0f}% confidence]")
        else:
            parts.append(f"{name}: {desc}")

    summary = ". ".join(parts)

    if verdict == "ATTRIBUTED":
        if agreeing == 3:
            summary += f". All 3 layers confirm {viewer_str}. High confidence attribution."
        else:
            summary += f". {agreeing} of 3 layers confirm {viewer_str}. Attribution confirmed."
    elif verdict == "PARTIAL":
        summary += f". Only 1 layer matched — PARTIAL attribution to {viewer_str}."
    else:
        summary += ". No valid session ID recovered — video may not be watermarked or heavily re-encoded."

    return summary
