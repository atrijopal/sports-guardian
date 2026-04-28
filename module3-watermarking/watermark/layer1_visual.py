import logging
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

import config
from watermark.common import (
    extract_frames, get_block_positions, get_noise_pattern,
    reassemble_video, rs_decode, rs_encode
)

logger = logging.getLogger(__name__)


def embed_frame(frame_bgr: np.ndarray, bits: list, frame_number: int) -> np.ndarray:
    bs = config.L1_BLOCK_SIZE
    frame_f = frame_bgr.astype(np.float32)
    h, w = frame_f.shape[:2]
    positions = get_block_positions(frame_number, len(bits), h, w, bs)
    for i, (row, col) in enumerate(positions):
        noise = get_noise_pattern(frame_number, i, bs)
        sign = 1 if bits[i] == 1 else -1
        for ch in range(3):
            block = frame_f[row:row+bs, col:col+bs, ch]
            block = block + sign * noise * config.L1_NOISE_STRENGTH
            frame_f[row:row+bs, col:col+bs, ch] = np.clip(block, 0, 255)
    return frame_f.astype(np.uint8)


def extract_frame(frame_bgr: np.ndarray, num_bits: int, frame_number: int) -> list:
    bs = config.L1_BLOCK_SIZE
    frame_f = frame_bgr.astype(np.float32)
    h, w = frame_f.shape[:2]
    positions = get_block_positions(frame_number, num_bits, h, w, bs)
    correlations = []
    for i, (row, col) in enumerate(positions):
        noise = get_noise_pattern(frame_number, i, bs)
        corr = 0.0
        for ch in range(3):
            block = frame_f[row:row+bs, col:col+bs, ch]
            block_norm = block - block.mean()
            corr += np.mean(block_norm * noise)
        corr /= 3.0
        correlations.append(corr / config.L1_NOISE_STRENGTH)
    return correlations


def embed_video(video_path: str, session_id_int: int, output_path: str) -> dict:
    bits = rs_encode(session_id_int)
    tmp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
    frames_watermarked = 0
    try:
        frames = extract_frames(video_path, tmp_dir)
        logger.info(f"[Layer1] Embedding into {len(frames)} frames")
        for idx, (frame_num, filepath) in enumerate(frames):
            if idx % config.L1_FRAME_INTERVAL != 0:
                continue
            try:
                frame = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                watermarked = embed_frame(frame, bits, frame_number=idx)
                cv2.imwrite(filepath, watermarked)
                frames_watermarked += 1
            except Exception as e:
                logger.warning(f"[Layer1] Skipping frame {idx}: {e}")
        reassemble_video(tmp_dir, video_path, output_path)
        logger.info(f"[Layer1] Embedded {frames_watermarked} frames → {output_path}")
        return {
            "frames_total": len(frames),
            "frames_watermarked": frames_watermarked,
            "bits_embedded": len(bits),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def extract_video(video_path: str) -> dict:
    num_bits = (config.SESSION_ID_BYTES + config.RS_ERROR_CORRECTION_SYMBOLS) * 8
    tmp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
    try:
        frames = extract_frames(video_path, tmp_dir)
        all_correlations = []
        frames_analyzed = 0
        for idx, (frame_num, filepath) in enumerate(frames):
            if idx % config.L1_FRAME_INTERVAL != 0:
                continue
            try:
                frame = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                corrs = extract_frame(frame, num_bits, frame_number=idx)
                all_correlations.append(corrs)
                frames_analyzed += 1
            except Exception as e:
                logger.warning(f"[Layer1] Skipping extract frame {idx}: {e}")

        if not all_correlations:
            return {"confidence": 0.0, "session_id_int": None,
                    "session_id_hex": None, "frames_analyzed": 0,
                    "bits_total": num_bits, "bits_reliable": 0}

        avg_corr = np.mean(all_correlations, axis=0)
        bits = []
        reliabilities = []
        for c in avg_corr:
            if abs(c) >= config.L1_CORRELATION_THRESHOLD:
                bits.append(1 if c > 0 else 0)
                reliabilities.append(abs(c))
            else:
                bits.append(-1)
                reliabilities.append(0.0)

        reliable_count = sum(1 for b in bits if b != -1)
        reliable_fraction = reliable_count / num_bits
        clean_bits = [1 if c >= 0 else 0 for c in avg_corr]
        session_id_int = rs_decode(clean_bits)
        session_id_hex = format(session_id_int, '016x') if session_id_int is not None else None

        logger.info(f"[Layer1] Extracted: id={session_id_hex}, confidence={reliable_fraction:.2f}")
        return {
            "session_id_int": session_id_int,
            "session_id_hex": session_id_hex,
            "confidence": reliable_fraction,
            "frames_analyzed": frames_analyzed,
            "bits_total": num_bits,
            "bits_reliable": reliable_count,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
