# fingerprint/layer1_visual.py — Visual pHash fingerprinting with normalization.

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image

import config
from fingerprint.normalize import canonicalize_frame

log = logging.getLogger(__name__)


def extract_frames(video_path: str, out_dir: str, interval_sec: float) -> list[tuple[float, str]]:
    """
    Extract one frame every interval_sec seconds using FFmpeg.
    Returns list of (timestamp_sec, filepath) tuples.
    """
    out_pattern = str(Path(out_dir) / "frame_%06d.jpg")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps=1/{interval_sec}",
        "-q:v", "3",
        out_pattern,
        "-y", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr.decode(errors='replace')}")

    frames = sorted(Path(out_dir).glob("frame_*.jpg"))
    # Reconstruct timestamps from frame index (1-based) and interval
    return [(i * interval_sec, str(f)) for i, f in enumerate(frames)]


def hash_frame(frame_path: str) -> str:
    """
    Load frame, canonicalize, compute pHash.
    Also compute pHash of horizontal flip.
    Return the lexicographically smaller hex string (mirror canonicalization).
    """
    bgr = cv2.imread(frame_path)
    if bgr is None:
        raise RuntimeError(f"Could not read frame: {frame_path}")

    canonical = canonicalize_frame(bgr)

    pil_normal = Image.fromarray(canonical)
    pil_flipped = Image.fromarray(np.fliplr(canonical))

    h_normal = str(imagehash.phash(pil_normal, hash_size=config.L1_HASH_SIZE))
    h_flipped = str(imagehash.phash(pil_flipped, hash_size=config.L1_HASH_SIZE))

    # Return the lexicographically smaller: makes mirroring a no-op
    return min(h_normal, h_flipped)


def generate_fingerprint(video_path: str) -> dict:
    """
    Extract frames, hash each, return fingerprint dict.
    Cleans up temp frames in all cases.
    """
    tmp_dir = tempfile.mkdtemp(prefix="fp_l1_")
    try:
        log.info("L1: extracting frames from %s", video_path)
        frames = extract_frames(
            video_path, tmp_dir, config.L1_FRAME_SAMPLE_INTERVAL_SEC
        )

        hashes = []
        for ts, fpath in frames:
            try:
                h = hash_frame(fpath)
                hashes.append({"timestamp": ts, "hash_hex": h})
            except Exception as e:
                log.warning("L1: skipping frame at %.1fs — %s", ts, e)

        log.info("L1: hashed %d frames", len(hashes))
        return {"frame_hashes": hashes}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def hamming_distance(hex1: str, hex2: str) -> int:
    """XOR two hex strings interpreted as ints, return popcount."""
    val = int(hex1, 16) ^ int(hex2, 16)
    return bin(val).count("1")


def match_fingerprints(suspect: dict, original: dict) -> float:
    """
    For each suspect frame hash, find the minimum Hamming distance to any
    original frame hash. Count as matched if distance <= L1_HAMMING_MATCH_THRESHOLD.
    Returns score = matched / total, or 0.0 if below MIN_MATCHED_FRAMES_RATIO.
    """
    suspect_hashes = [e["hash_hex"] for e in suspect.get("frame_hashes", [])]
    original_hashes = [e["hash_hex"] for e in original.get("frame_hashes", [])]

    if not suspect_hashes or not original_hashes:
        return 0.0

    matched = 0
    for sh in suspect_hashes:
        min_dist = min(hamming_distance(sh, oh) for oh in original_hashes)
        if min_dist <= config.L1_HAMMING_MATCH_THRESHOLD:
            matched += 1

    score = matched / len(suspect_hashes)
    if score < config.L1_MIN_MATCHED_FRAMES_RATIO:
        return 0.0
    return score
