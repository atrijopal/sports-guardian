import logging
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

import config
from watermark.common import (
    _get_rng, extract_frames, reassemble_video, rs_decode, rs_encode
)

logger = logging.getLogger(__name__)


def _get_dct_block_positions(frame_number: int, num_bits: int,
                              frame_h: int, frame_w: int) -> list:
    blocks_needed = num_bits * config.L3_BLOCKS_PER_BIT
    grid_rows = frame_h // 8
    grid_cols = frame_w // 8
    total_blocks = grid_rows * grid_cols

    if blocks_needed > total_blocks:
        blocks_per_bit = max(1, total_blocks // num_bits)
        blocks_needed = num_bits * blocks_per_bit
    else:
        blocks_per_bit = config.L3_BLOCKS_PER_BIT

    rng = _get_rng(frame_number)
    indices = rng.choice(total_blocks, size=blocks_needed, replace=False)
    result = []
    for bit_i in range(num_bits):
        bit_blocks = []
        for b in range(blocks_per_bit):
            idx = indices[bit_i * blocks_per_bit + b]
            grid_row = int(idx) // grid_cols
            grid_col = int(idx) % grid_cols
            bit_blocks.append((grid_row * 8, grid_col * 8))
        result.append(bit_blocks)
    return result


def embed_frame_dct(frame_bgr: np.ndarray, bits: list, frame_number: int) -> np.ndarray:
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)
    h, w = y.shape
    block_positions = _get_dct_block_positions(frame_number, len(bits), h, w)
    q = config.L3_QUANTIZATION_STEP
    tr, tc = config.L3_TARGET_COEFF

    for bit_i, bit in enumerate(bits):
        for (r, c) in block_positions[bit_i]:
            block = y[r:r+8, c:c+8]
            dct_block = cv2.dct(block)
            coeff = dct_block[tr, tc]
            n = round(coeff / q)
            if bit == 1:
                if n % 2 == 0:
                    n += 1
            else:
                if n % 2 != 0:
                    n += 1
            dct_block[tr, tc] = n * q
            y[r:r+8, c:c+8] = cv2.idct(dct_block)

    ycrcb[:, :, 0] = np.clip(y, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def extract_frame_dct(frame_bgr: np.ndarray, num_bits: int, frame_number: int) -> list:
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)
    h, w = y.shape
    block_positions = _get_dct_block_positions(frame_number, num_bits, h, w)
    q = config.L3_QUANTIZATION_STEP
    tr, tc = config.L3_TARGET_COEFF
    correlations = []

    for bit_i in range(num_bits):
        votes = []
        for (r, c) in block_positions[bit_i]:
            block = y[r:r+8, c:c+8]
            dct_block = cv2.dct(block)
            coeff = dct_block[tr, tc]
            n = round(coeff / q)
            votes.append(1.0 if n % 2 != 0 else -1.0)
        correlations.append(float(np.mean(votes)))

    return correlations


def embed_video(video_path: str, session_id_int: int, output_path: str) -> dict:
    bits = rs_encode(session_id_int)
    tmp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
    frames_watermarked = 0
    try:
        frames = extract_frames(video_path, tmp_dir)
        logger.info(f"[Layer3] Embedding into {len(frames)} frames")
        for idx, (frame_num, filepath) in enumerate(frames):
            if idx % config.L3_FRAME_INTERVAL != 0:
                continue
            try:
                frame = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                watermarked = embed_frame_dct(frame, bits, frame_number=idx)
                cv2.imwrite(filepath, watermarked)
                frames_watermarked += 1
            except Exception as e:
                logger.warning(f"[Layer3] Skipping frame {idx}: {e}")
        reassemble_video(tmp_dir, video_path, output_path)
        logger.info(f"[Layer3] Embedded {frames_watermarked} frames → {output_path}")
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
            if idx % config.L3_FRAME_INTERVAL != 0:
                continue
            try:
                frame = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                corrs = extract_frame_dct(frame, num_bits, frame_number=idx)
                all_correlations.append(corrs)
                frames_analyzed += 1
            except Exception as e:
                logger.warning(f"[Layer3] Skipping extract frame {idx}: {e}")

        if not all_correlations:
            return {"confidence": 0.0, "session_id_int": None,
                    "session_id_hex": None, "frames_analyzed": 0,
                    "bits_total": num_bits, "bits_reliable": 0}

        avg_corr = np.mean(all_correlations, axis=0)
        bits = []
        reliable_count = 0
        for c in avg_corr:
            if abs(c) >= config.L3_MIN_FRAME_AGREEMENT:
                bits.append(1 if c > 0 else 0)
                reliable_count += 1
            else:
                bits.append(-1)

        reliable_fraction = reliable_count / num_bits
        clean_bits = [1 if c >= 0 else 0 for c in avg_corr]
        session_id_int = rs_decode(clean_bits)
        session_id_hex = format(session_id_int, '016x') if session_id_int is not None else None

        logger.info(f"[Layer3] Extracted: id={session_id_hex}, confidence={reliable_fraction:.2f}")
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
