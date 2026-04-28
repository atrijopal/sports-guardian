import logging
import shutil
import time
from pathlib import Path

import config
from session_registry import SessionRegistry
from watermark import layer1_visual, layer2_audio, layer3_dct

logger = logging.getLogger(__name__)


def embed_full(video_path: str,
               viewer_name: str,
               registry: SessionRegistry,
               account_id: str = "",
               region: str = "",
               platform: str = "",
               ip_address: str = "") -> dict:
    source_name = Path(video_path).name
    session = registry.create_session(
        viewer_name=viewer_name,
        source_video=source_name,
        account_id=account_id,
        region=region,
        platform=platform,
        ip_address=ip_address,
    )
    session_id_int = session["session_id_int"]
    session_id_hex = session["session_id_hex"]

    source_stem = Path(video_path).stem
    viewer_slug = viewer_name.lower().replace(" ", "_")[:20]
    output_filename = f"{viewer_slug}_{source_stem}.mp4"
    output_path = Path(config.WATERMARKED_DIR) / output_filename
    Path(config.WATERMARKED_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    tmp1 = Path(config.TEMP_DIR) / f"tmp_l1_{session_id_hex}.mp4"
    tmp2 = Path(config.TEMP_DIR) / f"tmp_l2_{session_id_hex}.mp4"
    layers_embedded = []
    start = time.time()

    try:
        # Layer 1
        try:
            l1_result = layer1_visual.embed_video(video_path, session_id_int, str(tmp1))
            layers_embedded.append("layer1")
            logger.info(f"[Embedder] L1 done: {l1_result}")
            l1_input = str(tmp1)
        except Exception as e:
            logger.error(f"[Embedder] Layer 1 failed: {e}")
            l1_input = video_path

        # Layer 2 (input = Layer 1 output or original)
        try:
            l2_result = layer2_audio.embed_video(l1_input, session_id_int, str(tmp2))
            layers_embedded.append("layer2")
            logger.info(f"[Embedder] L2 done: {l2_result}")
            l2_input = str(tmp2)
        except Exception as e:
            logger.error(f"[Embedder] Layer 2 failed: {e}")
            l2_input = l1_input

        # Layer 3 (input = Layer 2 output or best available)
        try:
            l3_result = layer3_dct.embed_video(l2_input, session_id_int, str(output_path))
            layers_embedded.append("layer3")
            logger.info(f"[Embedder] L3 done: {l3_result}")
        except Exception as e:
            logger.error(f"[Embedder] Layer 3 failed: {e}")
            # Fall back to best available output
            if Path(l2_input).exists():
                shutil.copy2(l2_input, str(output_path))

        elapsed = time.time() - start
        registry.update_watermarked_file(session_id_hex, str(output_path), layers_embedded)

        return {
            "session_id_hex": session_id_hex,
            "session_id_int": session_id_int,
            "viewer_name": viewer_name,
            "output_path": str(output_path),
            "output_filename": output_filename,
            "layers_embedded": layers_embedded,
            "processing_seconds": round(elapsed, 1),
        }

    except Exception as e:
        logger.error(f"[Embedder] Fatal error: {e}")
        return {"error": str(e), "session_id_hex": session_id_hex}

    finally:
        for tmp in [tmp1, tmp2]:
            if tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass
