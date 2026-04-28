# fingerprint/layer4_dna.py — Event-peak DNA fingerprinting with fuzzy substring match.

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks

import config

log = logging.getLogger(__name__)


def _extract_visual_energy(video_path: str, tmp_dir: str) -> list[float]:
    """
    Extract 1-fps frames, compute mean abs diff between consecutive frames.
    Returns a list of float energy values (length ≈ duration in seconds).
    """
    frames_dir = Path(tmp_dir) / "frames"
    frames_dir.mkdir()

    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", "fps=1",
        "-q:v", "5",
        str(frames_dir / "f_%06d.jpg"),
        "-y", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        log.warning("L4: ffmpeg 1fps extraction failed — %s", result.stderr.decode(errors="replace"))
        return []

    frame_paths = sorted(frames_dir.glob("f_*.jpg"))
    if not frame_paths:
        return []

    # Read all frames as grayscale
    grays = []
    for fp in frame_paths:
        img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            grays.append(img.astype(np.float32))

    if len(grays) < 2:
        return [0.0] * len(grays)

    # Energy = mean absolute pixel difference between consecutive frames
    energy = [0.0]  # first frame has no predecessor
    for i in range(1, len(grays)):
        diff = np.mean(np.abs(grays[i] - grays[i - 1]))
        energy.append(float(diff))

    return energy


def _extract_audio_energy(video_path: str, tmp_dir: str) -> list[float]:
    """
    Extract audio WAV, compute 1-second RMS energy via librosa.
    Returns normalized energy list. Returns [] gracefully if no audio.
    """
    import soundfile as sf
    import librosa

    wav_path = str(Path(tmp_dir) / "audio_l4.wav")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "22050", "-ac", "1",
        wav_path,
        "-y", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, shell=False)
    if result.returncode != 0:
        log.warning("L4: no audio for energy extraction")
        return []

    try:
        y, sr = librosa.load(wav_path, sr=22050, mono=True)
        hop_length = sr  # 1-second hops
        rms = librosa.feature.rms(y=y, frame_length=sr * 2, hop_length=hop_length)[0]
        energy = rms.tolist()
        return energy
    except Exception as e:
        log.warning("L4: audio energy extraction failed — %s", e)
        return []


def extract_energy_signals(video_path: str) -> dict:
    """
    Return {"visual": [...], "audio": [...], "duration": N}.
    Both arrays are 1-Hz sampled over the video duration.
    """
    tmp_dir = tempfile.mkdtemp(prefix="fp_l4_")
    try:
        log.info("L4: extracting visual energy")
        visual = _extract_visual_energy(video_path, tmp_dir)

        log.info("L4: extracting audio energy")
        audio = _extract_audio_energy(video_path, tmp_dir)

        duration = len(visual)
        # Pad/trim audio to match visual length
        if len(audio) < duration:
            audio = audio + [0.0] * (duration - len(audio))
        else:
            audio = audio[:duration]

        return {"visual": visual, "audio": audio, "duration": duration}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _normalize_signal(signal: list[float]) -> list[float]:
    """Normalize a signal to [0, 1]. Returns zeros if flat."""
    arr = np.array(signal, dtype=np.float32)
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-6:
        return [0.0] * len(signal)
    return ((arr - lo) / (hi - lo)).tolist()


def detect_peaks(signal: list[float], prominence: float) -> list[int]:
    """
    Find peaks in a normalized signal using scipy.
    Returns list of peak indices (seconds into video).
    """
    if len(signal) < 3:
        return []
    normalized = _normalize_signal(signal)
    arr = np.array(normalized)
    peaks, _ = find_peaks(arr, prominence=prominence)
    return peaks.tolist()


def build_dna_string(energy: dict) -> tuple[str, list[dict]]:
    """
    Detect peaks in visual and audio signals.
    Merge into a sorted timeline, encode as a DNA string.

    Event character: 'V' = visual peak, 'A' = audio peak.
    Gap between consecutive events quantized to:
      's' = short  (<3s)
      'm' = medium (3–8s)
      'l' = long   (>8s)

    Returns (dna_string, events_list).
    Speed invariance relies on RATIO encoding, not absolute gaps.
    """
    visual_peaks = detect_peaks(energy.get("visual", []), config.L4_PEAK_PROMINENCE_VISUAL)
    audio_peaks = detect_peaks(energy.get("audio", []), config.L4_PEAK_PROMINENCE_AUDIO)

    events = []
    for t in visual_peaks:
        events.append({"t": float(t), "type": "V"})
    for t in audio_peaks:
        events.append({"t": float(t), "type": "A"})

    events.sort(key=lambda e: e["t"])

    if len(events) < 2:
        # Not enough events — return whatever we have
        dna = "".join(e["type"] for e in events)
        return dna, events

    # Build DNA string with quantized gap characters
    parts = [events[0]["type"]]
    for i in range(1, len(events)):
        gap = events[i]["t"] - events[i - 1]["t"]
        if gap < 3.0:
            gap_char = "s"
        elif gap <= 8.0:
            gap_char = "m"
        else:
            gap_char = "l"
        parts.append(gap_char)
        parts.append(events[i]["type"])

    dna = "".join(parts)
    return dna, events


def generate_fingerprint(video_path: str) -> dict:
    """
    Full pipeline: extract energies → build DNA → return dict.
    """
    log.info("L4: generating DNA fingerprint for %s", video_path)
    energy = extract_energy_signals(video_path)
    dna, events = build_dna_string(energy)
    log.info("L4: DNA length=%d, events=%d", len(dna), len(events))
    return {"dna_string": dna, "events": events}


def match_fingerprints(suspect: dict, original: dict) -> float:
    """
    Fuzzy substring match of suspect DNA within original DNA.
    Returns score in [0.0, 1.0].
    Returns 0.0 if DNA is too short or score below threshold.
    """
    from rapidfuzz import fuzz

    suspect_dna = suspect.get("dna_string", "")
    original_dna = original.get("dna_string", "")

    # Minimum meaningful DNA: L4_MIN_DNA_LENGTH events + gap chars between them
    min_len = config.L4_MIN_DNA_LENGTH * 2 - 1
    if len(suspect_dna) < min_len or not original_dna:
        return 0.0

    score = fuzz.partial_ratio(suspect_dna, original_dna)

    if score < config.L4_FUZZY_MATCH_THRESHOLD:
        return 0.0

    return score / 100.0
