import logging
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal as scipy_signal

import config
from watermark.common import extract_audio, replace_audio, rs_decode, rs_encode

logger = logging.getLogger(__name__)


def _generate_tone(bit_value: int, duration_samples: int,
                   sample_rate: int, amplitude: float) -> np.ndarray:
    t = np.linspace(0, duration_samples / sample_rate,
                    duration_samples, endpoint=False)
    carrier = np.sin(2 * np.pi * config.L2_CARRIER_FREQ * t)
    if bit_value == 1:
        return carrier * amplitude
    else:
        return -carrier * amplitude


def embed_audio(samples: np.ndarray, sample_rate: int, bits: list) -> np.ndarray:
    if samples.ndim > 1:
        samples = samples[:, 0]
    bit_samples = int(config.L2_BIT_DURATION_MS / 1000 * sample_rate)
    repeat_interval_samples = int(config.L2_REPEAT_INTERVAL_SEC * sample_rate)
    repeats = max(1, int(len(samples) / repeat_interval_samples))
    modified = samples.copy().astype(np.float64)

    for r in range(repeats):
        start_sample = r * repeat_interval_samples
        for i, bit in enumerate(bits):
            bit_start = start_sample + i * bit_samples
            bit_end = bit_start + bit_samples
            if bit_end > len(modified):
                break
            tone = _generate_tone(bit, bit_samples, sample_rate, config.L2_AMPLITUDE)
            modified[bit_start:bit_end] += tone

    return np.clip(modified, -1.0, 1.0)


def extract_audio_watermark(samples: np.ndarray, sample_rate: int, num_bits: int) -> dict:
    if samples.ndim > 1:
        samples = samples[:, 0]

    # Early exit: check band energy
    sos = scipy_signal.butter(
        4, [config.L2_BANDPASS_LOW, config.L2_BANDPASS_HIGH],
        btype='bandpass', fs=sample_rate, output='sos'
    )
    try:
        filtered = scipy_signal.sosfiltfilt(sos, samples)
    except Exception:
        return {"confidence": 0.0, "session_id_int": None, "session_id_hex": None,
                "status": "filter_error", "repetitions_analyzed": 0,
                "bits_total": num_bits, "bits_reliable": 0}

    rms = np.sqrt(np.mean(filtered ** 2))
    if rms < 1e-6:
        return {"confidence": 0.0, "session_id_int": None, "session_id_hex": None,
                "status": "no_signal", "repetitions_analyzed": 0,
                "bits_total": num_bits, "bits_reliable": 0}

    bit_samples = int(config.L2_BIT_DURATION_MS / 1000 * sample_rate)
    repeat_interval_samples = int(config.L2_REPEAT_INTERVAL_SEC * sample_rate)
    repeats = max(1, int(len(filtered) / repeat_interval_samples))

    all_correlations = [[] for _ in range(num_bits)]
    reps_analyzed = 0

    for r in range(repeats):
        start = r * repeat_interval_samples
        rep_complete = True
        for i in range(num_bits):
            bit_start = start + i * bit_samples
            bit_end = bit_start + bit_samples
            if bit_end > len(filtered):
                rep_complete = False
                break
            segment = filtered[bit_start:bit_end]
            t = np.linspace(0, bit_samples / sample_rate, bit_samples, endpoint=False)
            ref = np.sin(2 * np.pi * config.L2_CARRIER_FREQ * t)
            corr = float(np.mean(segment * ref))
            all_correlations[i].append(corr)
        if rep_complete:
            reps_analyzed += 1

    bits_extracted = []
    reliable_count = 0
    for i in range(num_bits):
        if not all_correlations[i]:
            bits_extracted.append(-1)
            continue
        avg_corr = float(np.mean(all_correlations[i]))
        if avg_corr > config.L2_PHASE_DETECTION_THRESHOLD:
            bits_extracted.append(1)
            reliable_count += 1
        elif avg_corr < -config.L2_PHASE_DETECTION_THRESHOLD:
            bits_extracted.append(0)
            reliable_count += 1
        else:
            bits_extracted.append(-1)

    reliable_fraction = reliable_count / num_bits if num_bits > 0 else 0.0
    clean_bits = [1 if b == 1 else 0 for b in bits_extracted]
    session_id_int = rs_decode(clean_bits)
    session_id_hex = format(session_id_int, '016x') if session_id_int is not None else None

    logger.info(f"[Layer2] Extracted: id={session_id_hex}, confidence={reliable_fraction:.2f}, reps={reps_analyzed}")
    return {
        "session_id_int": session_id_int,
        "session_id_hex": session_id_hex,
        "confidence": reliable_fraction,
        "status": "ok",
        "repetitions_analyzed": reps_analyzed,
        "bits_total": num_bits,
        "bits_reliable": reliable_count,
    }


def embed_video(video_path: str, session_id_int: int, output_path: str) -> dict:
    tmp_audio = Path(config.TEMP_DIR) / f"_l2audio_{Path(video_path).stem}.wav"
    try:
        has_audio = extract_audio(video_path, str(tmp_audio))
        if not has_audio:
            import shutil
            shutil.copy2(video_path, output_path)
            logger.info("[Layer2] No audio track — video copied unchanged")
            return {"status": "no_audio", "confidence_expected": 0}

        samples, sr = sf.read(str(tmp_audio))
        bits = rs_encode(session_id_int)
        watermarked_samples = embed_audio(samples, sr, bits)
        sf.write(str(tmp_audio), watermarked_samples, sr, subtype='PCM_16')
        replace_audio(video_path, str(tmp_audio), output_path)
        logger.info(f"[Layer2] Embedded {len(bits)} bits into audio")
        return {"status": "ok", "bits_embedded": len(bits)}
    finally:
        if tmp_audio.exists():
            tmp_audio.unlink()


def extract_video(video_path: str) -> dict:
    tmp_audio = Path(config.TEMP_DIR) / f"_l2ext_{Path(video_path).stem}.wav"
    num_bits = (config.SESSION_ID_BYTES + config.RS_ERROR_CORRECTION_SYMBOLS) * 8
    try:
        has_audio = extract_audio(video_path, str(tmp_audio))
        if not has_audio:
            return {"confidence": 0.0, "session_id_int": None,
                    "session_id_hex": None, "status": "no_audio",
                    "repetitions_analyzed": 0,
                    "bits_total": num_bits, "bits_reliable": 0}

        samples, sr = sf.read(str(tmp_audio))
        result = extract_audio_watermark(samples, sr, num_bits)
        return result
    finally:
        if tmp_audio.exists():
            tmp_audio.unlink()
