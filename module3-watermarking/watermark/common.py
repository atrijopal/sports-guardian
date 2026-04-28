import hashlib
import hmac
import logging
import subprocess
from pathlib import Path

import numpy as np
from reedsolo import RSCodec, ReedSolomonError

import config

logger = logging.getLogger(__name__)

# ---- Reed-Solomon Error Correction ----

_rs = RSCodec(config.RS_ERROR_CORRECTION_SYMBOLS)


def rs_encode(session_id_int: int) -> list:
    data_bytes = session_id_int.to_bytes(config.SESSION_ID_BYTES, 'big')
    encoded_bytes = _rs.encode(data_bytes)
    bits = []
    for byte in encoded_bytes:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def rs_decode(bits: list):
    # Pad to multiple of 8
    padded = list(bits)
    while len(padded) % 8 != 0:
        padded.append(0)
    encoded_bytes = bytearray()
    for i in range(0, len(padded), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | padded[i + j]
        encoded_bytes.append(byte)
    try:
        decoded = _rs.decode(bytes(encoded_bytes))
        # reedsolo returns (decoded_msg, decoded_msgecc, errata_pos) in newer versions
        if isinstance(decoded, tuple):
            decoded_bytes = decoded[0]
        else:
            decoded_bytes = decoded
        return int.from_bytes(decoded_bytes[:config.SESSION_ID_BYTES], 'big')
    except (ReedSolomonError, Exception):
        return None


# ---- HMAC-Based Key Derivation for Position Generation ----

def _get_rng(frame_number: int) -> np.random.RandomState:
    msg = f"{config.WATERMARK_SALT}:{frame_number}".encode()
    seed_bytes = hmac.new(
        config.WATERMARK_SECRET_KEY.encode(),
        msg,
        hashlib.sha256
    ).digest()
    seed_int = int.from_bytes(seed_bytes[:4], 'big')
    return np.random.RandomState(seed_int)


def get_block_positions(frame_number: int, num_bits: int,
                        frame_h: int, frame_w: int,
                        block_size: int) -> list:
    rows_in_grid = frame_h // block_size
    cols_in_grid = frame_w // block_size
    total_blocks = rows_in_grid * cols_in_grid
    if num_bits > total_blocks:
        raise ValueError(
            f"Video resolution too small for watermarking. "
            f"Need at least {num_bits * block_size * block_size} pixels "
            f"(have {frame_h * frame_w})"
        )
    rng = _get_rng(frame_number)
    indices = rng.choice(total_blocks, size=num_bits, replace=False)
    positions = []
    for idx in indices:
        grid_row = int(idx) // cols_in_grid
        grid_col = int(idx) % cols_in_grid
        positions.append((grid_row * block_size, grid_col * block_size))
    return positions


def get_noise_pattern(frame_number: int, bit_index: int,
                      block_size: int) -> np.ndarray:
    msg = f"{config.WATERMARK_SALT}:{frame_number}:{bit_index}".encode()
    seed_bytes = hmac.new(
        config.WATERMARK_SECRET_KEY.encode(),
        msg,
        hashlib.sha256
    ).digest()
    seed_int = int.from_bytes(seed_bytes[:4], 'big')
    rng = np.random.RandomState(seed_int)
    return rng.choice([-1.0, 1.0], size=(block_size, block_size))


# ---- FFmpeg Utilities ----

def run_ffmpeg(args: list, description: str = "") -> None:
    result = subprocess.run(
        ["ffmpeg"] + args,
        capture_output=True, text=True, shell=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed ({description}): {result.stderr[-500:]}"
        )


def get_fps(video_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(video_path)],
            capture_output=True, text=True, shell=False
        )
        output = result.stdout.strip()
        if "/" in output:
            num, den = output.split("/")
            return float(num) / float(den)
        return float(output)
    except Exception:
        return 30.0


def get_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(video_path)],
            capture_output=True, text=True, shell=False
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def extract_frames(video_path: str, output_dir: str) -> list:
    run_ffmpeg(
        ["-y", "-i", str(video_path), "-q:v", "1",
         str(Path(output_dir) / "frame_%06d.png")],
        description="extract frames"
    )
    frames = sorted(Path(output_dir).glob("frame_*.png"))
    return [(i + 1, str(f)) for i, f in enumerate(frames)]


def reassemble_video(frames_dir: str, original_video: str,
                     output_path: str) -> None:
    fps = get_fps(original_video)
    temp_silent = str(Path(output_path).parent / ("_silent_" + Path(output_path).name))
    try:
        run_ffmpeg(
            ["-y", "-framerate", str(fps),
             "-i", str(Path(frames_dir) / "frame_%06d.png"),
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p", temp_silent],
            description="frames to silent video"
        )
        run_ffmpeg(
            ["-y", "-i", temp_silent, "-i", str(original_video),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-map", "0:v:0", "-map", "1:a:0?", "-shortest",
             str(output_path)],
            description="add audio to video"
        )
    finally:
        silent_path = Path(temp_silent)
        if silent_path.exists():
            silent_path.unlink()


def extract_audio(video_path: str, output_wav: str) -> bool:
    # Check if video has audio stream
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(video_path)],
        capture_output=True, text=True, shell=False
    )
    if not probe.stdout.strip():
        return False
    try:
        run_ffmpeg(
            ["-y", "-i", str(video_path), "-vn",
             "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
             str(output_wav)],
            description="extract audio"
        )
        output = Path(output_wav)
        if not output.exists() or output.stat().st_size == 0:
            return False
        return True
    except RuntimeError:
        return False


def replace_audio(video_path: str, audio_wav: str,
                  output_path: str) -> None:
    run_ffmpeg(
        ["-y", "-i", str(video_path), "-i", str(audio_wav),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-map", "0:v:0", "-map", "1:a:0", "-shortest",
         str(output_path)],
        description="replace audio"
    )
