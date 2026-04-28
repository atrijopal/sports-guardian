# fingerprint/layer2_audio.py — Chromaprint audio fingerprinting + sliding window match.

import logging
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

import config

log = logging.getLogger(__name__)


def extract_audio_wav(video_path: str, out_path: str) -> None:
    """
    Extract audio as 44.1kHz mono WAV via FFmpeg.
    If the video has no audio, write 1 second of silence so downstream
    code doesn't crash. Logs a warning in that case.
    """
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(config.L2_SAMPLE_RATE),
        "-ac", "1",
        str(out_path),
        "-y", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, shell=False)

    if result.returncode != 0:
        # Likely no audio stream — write 1s silence
        log.warning("L2: no audio stream detected, using silence placeholder")
        _write_silence_wav(out_path)


def _write_silence_wav(path: str) -> None:
    """Write a minimal 1-second silent WAV at 44100 Hz mono 16-bit."""
    sample_rate = config.L2_SAMPLE_RATE
    num_samples = sample_rate  # 1 second
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))       # chunk size
        f.write(struct.pack("<H", 1))        # PCM
        f.write(struct.pack("<H", 1))        # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))        # block align
        f.write(struct.pack("<H", 16))       # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


def compute_chromaprint(wav_path: str) -> tuple[list[int], float]:
    """
    Call fpcalc -raw on the WAV file.
    Returns (list_of_32bit_ints, duration_sec).
    Parses stdout for DURATION= and FINGERPRINT= lines.
    """
    cmd = ["fpcalc", "-raw", str(wav_path)]
    result = subprocess.run(cmd, capture_output=True, shell=False)

    if result.returncode != 0:
        log.warning("L2: fpcalc failed — %s", result.stderr.decode(errors="replace"))
        return [], 0.0

    stdout = result.stdout.decode(errors="replace")
    duration = 0.0
    ints = []

    for line in stdout.splitlines():
        if line.startswith("DURATION="):
            try:
                duration = float(line.split("=", 1)[1])
            except ValueError:
                pass
        elif line.startswith("FINGERPRINT="):
            raw = line.split("=", 1)[1].strip()
            if raw:
                try:
                    ints = [int(x) for x in raw.split(",") if x]
                except ValueError:
                    log.warning("L2: could not parse fingerprint ints")

    return ints, duration


def generate_fingerprint(video_path: str) -> dict:
    """
    Extract audio WAV → Chromaprint → return fingerprint dict.
    Cleans up temp files in all cases.
    """
    tmp_dir = tempfile.mkdtemp(prefix="fp_l2_")
    try:
        wav_path = str(Path(tmp_dir) / "audio.wav")
        log.info("L2: extracting audio from %s", video_path)
        extract_audio_wav(video_path, wav_path)

        log.info("L2: computing Chromaprint")
        ints, duration = compute_chromaprint(wav_path)

        log.info("L2: %d fingerprint ints, duration=%.1fs", len(ints), duration)
        return {"chromaprint_ints": ints, "duration": duration}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def xor_distance(a: int, b: int) -> int:
    """Popcount of (a XOR b) masked to 32 bits."""
    return bin((a ^ b) & 0xFFFFFFFF).count("1")


def sliding_window_match(suspect_ints: list[int], original_ints: list[int]) -> float:
    """
    Slide the shorter fingerprint across the longer one.
    At each offset, compute average XOR bit distance across the overlap.
    Returns score = 1.0 - (best_avg_bits / 32.0), clamped to [0, 1].
    Returns 0.0 if best match exceeds L2_XOR_BIT_THRESHOLD or input is too short.
    """
    if not suspect_ints or not original_ints:
        return 0.0

    # Ensure suspect is the shorter one
    if len(suspect_ints) > len(original_ints):
        suspect_ints, original_ints = original_ints, suspect_ints

    n_sus = len(suspect_ints)
    n_ori = len(original_ints)

    best_avg = 32.0
    for offset in range(n_ori - n_sus + 1):
        total_bits = sum(
            xor_distance(suspect_ints[i], original_ints[offset + i])
            for i in range(n_sus)
        )
        avg_bits = total_bits / n_sus
        if avg_bits < best_avg:
            best_avg = avg_bits

    if best_avg > config.L2_XOR_BIT_THRESHOLD:
        return 0.0

    score = 1.0 - (best_avg / 32.0)
    return max(0.0, min(1.0, score))


def match_fingerprints(suspect: dict, original: dict) -> float:
    """Unpack dicts and run sliding window match."""
    return sliding_window_match(
        suspect.get("chromaprint_ints", []),
        original.get("chromaprint_ints", []),
    )
