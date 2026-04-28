# Module 3 — Source Attribution & Watermarking Engine
## Hackathon Demo Implementation Plan (for Claude Code)

---

## 0. Read This First (Context for Claude Code)

You are building a **forensic watermarking system** that embeds invisible, unique session IDs into video files and later extracts them — even after the video has been mirrored, cropped, recolored, sped up, muted, re-encoded, or logo-stamped.

This is **Module 3** of a larger "Digital Asset Protection" system. The three modules answer three different questions:
- Module 1 (Fingerprinting): "Is this our content?"
- Module 2 (Threat Intel): "Where is piracy happening?"
- Module 3 (Watermarking): **"WHO leaked it?"**

**This system shares the exact same demo videos and attack pipeline as Module 1.** There is no new video preparation needed. The workflow is:
1. Take a source video from Module 1's `demo_videos/` folder
2. Watermark it three times with three different session IDs → three "viewer copies"
3. Run Module 1's `attack_generator.py` on one viewer copy → attacked clips
4. Feed the attacked clips into the extractor → recovers the session ID
5. Look up the session ID in the registry → reveals exactly which viewer leaked it

**There is NO machine learning, NO NLP, NO AI model in this module.** This is pure Digital Signal Processing (DSP) and mathematics: numpy array operations, scipy signal processing, FFT transforms, DCT operations, and Reed-Solomon error correction. The "intelligence" is in the mathematical robustness of the watermarking methods, not in any model.

**This is a hackathon demo.** Optimize for:
1. **Correctness of the math** — the extraction must recover the right session ID after attacks
2. **Shared pipeline with Module 1** — same videos, same attacks, same FFmpeg commands
3. **Simple storage** — JSON file for session registry, no database
4. **Windows compatibility** — FFmpeg in PATH (already installed for Module 1), Python + pip only
5. **~10 hour build budget**

**The target demo experience:**
- Left panel: "Embed Watermark" — pick a source video from `demo_videos/`, enter a viewer name, click Embed → system produces a watermarked copy
- Repeat 3 times to create 3 different viewer copies (Viewer A, Viewer B, Viewer C)
- Run `attack_generator.py` on Viewer B's copy → 8 attacked versions
- Right panel: "Extract & Attribute" — upload any attacked clip → system recovers the session ID, identifies Viewer B, shows per-layer confidence breakdown
- Judges see: the SAME attacked clip that Module 1 said "this is our content" now also reveals "and Viewer B from ESPN US leaked it"

---

## 1. What the System Does (Broader View)

### The Problem
Knowing a video is pirated (Module 1) is only half the battle. To stop leaks at the source, you need to know **which specific viewer** redistributed the content. If a broadcaster sends the same feed to thousands of viewers and a pirated clip appears online, who is responsible?

### The Solution: Invisible Unique Fingerprints Per Viewer
Before any video reaches a viewer, invisibly embed a unique session ID using three independent mathematical methods. Each viewer gets a slightly different version of the video — differences invisible to human perception but recoverable by software. When a pirated clip appears, extract the session ID and look it up in a registry to identify the leaker.

### Three Layers, Three Mathematical Methods

**Layer 1 — Spread Spectrum Visual Watermark**
Adds a low-amplitude pseudo-random noise pattern across large pixel regions. Each bit of the session ID controls the polarity (+/-) of the noise in one region. Extraction detects the polarity via correlation. Survives re-encoding, color grading, and compression because the noise is spread across thousands of pixels rather than isolated single bits (which is why LSB/least-significant-bit watermarking dies on any re-encode).

**Layer 2 — BPSK Audio Watermark (High-Frequency Tones)**
Embeds the session ID as 19,000 Hz tone bursts in the frequency range humans cannot hear. Uses Binary Phase-Shift Keying: bit 1 = 0° phase, bit 0 = 180° phase. Repeated every 10 seconds throughout the audio track. Extracted using a bandpass filter + Hilbert transform to detect phase. Survives re-encoding, cam-ripping, and format conversion.

**Layer 3 — DCT Structural Watermark (Frequency Domain)**
Modifies mid-frequency DCT (Discrete Cosine Transform) coefficients in 8×8 pixel blocks — the same mathematical domain video compression operates in. Uses Quantization Index Modulation: nudges each target coefficient to be an odd or even multiple of a step size to encode a bit. Survives cropping, resizing, and aspect ratio changes — the attacks that defeat Layer 1 — because frequency-domain structure is preserved across geometric transforms.

**Session Registry**
A JSON file mapping session IDs to viewer metadata: name, account ID, region, platform, IP address, timestamp, source video, watermarked file path. When extraction recovers a session ID, the registry lookup reveals the leaker.

### Reed-Solomon Error Correction (All Three Layers)
Before embedding, the 64-bit session ID is encoded with Reed-Solomon error correction, expanding it to ~96 bits. This means the correct session ID can be recovered even if ~15% of the embedded bits are corrupted by attacks, compression, or re-encoding. This is the difference between a watermarking system that works reliably in the real world and one that only works in a pristine lab environment.

### The 2-of-3 Fusion Rule
Each layer independently extracts a session ID with a confidence score. Attribution is confirmed only if **at least 2 of 3 layers agree on the same session ID**. This prevents false attribution from noise and means a pirate would have to defeat multiple independent systems simultaneously — which typically requires so much processing that the video becomes unwatchable.

### Why This Connects to Module 1
- Same source videos in `demo_videos/`
- Same `attack_generator.py` attacks
- Module 1 answers: "This is our content (confidence 94%)"
- Module 3 answers: "And Viewer B from ESPN US leaked it (confidence 82%)"
- The session registry stores the Module 1 fingerprint hash alongside the session ID — the two modules cross-reference through the same piece of content

---

## 2. Tech Stack (All Free, No New Installs Beyond Module 1)

**Language:** Python 3.10+

**External binary (already installed for Module 1):**
- `ffmpeg` — frame extraction, audio extraction, video reassembly

**Python packages:**
```
fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9
opencv-python>=4.9        # already installed for Module 1
numpy>=1.26               # already installed for Module 1
Pillow>=10.0              # already installed for Module 1
scipy>=1.12               # already installed for Module 1
soundfile>=0.12           # already installed for Module 1
reedsolo>=1.7             # NEW — Reed-Solomon error correction
```

The only new package compared to Module 1 is `reedsolo`. Everything else is already installed.

**Storage:** JSON file (`session_registry.json`). No SQL, no database server.

**Shared with Module 1:**
- `demo_videos/` folder and all source videos
- `demo_videos/attacks/` folder and all attacked clips
- `attack_generator.py` — copy or symlink it into the Module 3 folder
- FFmpeg binary (already in PATH)

---

## 3. Project Structure

```
module3-watermarking/
├── requirements.txt
├── README.md
├── config.py                        # Secret keys, thresholds, all tunables
├── app.py                           # FastAPI server
├── session_registry.py              # JSON-backed session database
├── watermark/
│   ├── __init__.py
│   ├── common.py                    # Shared: key generation, error correction, frame I/O
│   ├── layer1_visual.py             # Spread spectrum visual watermarking
│   ├── layer2_audio.py              # BPSK high-frequency audio watermarking
│   ├── layer3_dct.py                # DCT coefficient watermarking
│   ├── embedder.py                  # Orchestrates all 3 layers: embed pipeline
│   └── extractor.py                 # Orchestrates all 3 layers: extract + fusion
├── static/
│   └── index.html                   # Two-panel UI: embed + extract
├── demo_videos/                     # SYMLINK or COPY from Module 1
│   └── attacks/                     # SYMLINK or COPY from Module 1
├── watermarked_outputs/             # Watermarked viewer copies stored here
├── temp_processing/                 # Temp frames/audio during processing (auto-cleaned)
├── session_registry.json            # Created at runtime
└── attack_generator.py              # COPIED from Module 1 — identical script
```

---

## 4. Config File (`config.py`)

All tunable parameters in one place. Tune thresholds here during testing, not inside module files.

```python
# config.py

# ---- Secret Keys ----
# CRITICAL: The same key must be used for both embed and extract.
# Changing this key makes all existing watermarks unextractable.
# In production these would be stored in a secure key vault.
WATERMARK_SECRET_KEY = "hackathon-demo-secret-key-2024"
WATERMARK_SALT = "sports-asset-protection-v1"

# ---- Session ID ----
SESSION_ID_BITS = 64                # 64-bit ID = 18 quintillion unique sessions
SESSION_ID_BYTES = 8                # = 64 / 8

# ---- Reed-Solomon Error Correction ----
RS_ERROR_CORRECTION_SYMBOLS = 10    # 10 symbols of redundancy
# 64 bits = 8 bytes data + 10 bytes RS = 18 bytes total = 144 bits to embed
# Can correct up to 5 bytes (40 bits) of corruption — ~27% of total bits
# Reduce this if embedding is too slow. Minimum useful value: 4

# ---- Layer 1: Spread Spectrum Visual ----
L1_FRAME_INTERVAL = 5               # Watermark every Nth frame (5 = every 5th)
L1_BLOCK_SIZE = 32                  # Pixel region size per bit (32x32)
L1_NOISE_STRENGTH = 4.0             # Noise amplitude (higher = more robust, more visible)
                                    # 4.0 is invisible to eye, barely survives heavy attack
                                    # If attacks fail, try 6.0 or 8.0
L1_CORRELATION_THRESHOLD = 0.08     # Min |correlation| to classify a bit confidently
L1_MIN_FRAME_AGREEMENT = 0.45       # Min fraction of frames agreeing on each bit

# ---- Layer 2: Audio BPSK ----
L2_CARRIER_FREQ = 19000             # 19 kHz carrier — above human hearing
L2_BIT_DURATION_MS = 50            # 50ms per bit
L2_AMPLITUDE = 0.008                # Very low amplitude (inaudible at normal volume)
L2_REPEAT_INTERVAL_SEC = 10         # Repeat full ID sequence every 10 seconds
L2_SAMPLE_RATE = 44100              # Must match audio extraction sample rate
L2_PHASE_DETECTION_THRESHOLD = 0.2  # Min correlation magnitude to classify a phase
L2_BANDPASS_LOW = 18000             # Bandpass filter lower bound (Hz)
L2_BANDPASS_HIGH = 20500            # Bandpass filter upper bound (Hz)

# ---- Layer 3: DCT Structural ----
L3_DCT_BLOCK_SIZE = 8               # Standard 8x8 DCT blocks (matches JPEG/H.264)
L3_TARGET_COEFF = (4, 3)            # Mid-frequency coefficient position within block
                                    # (4,3) is a well-known mid-frequency sweet spot
L3_QUANTIZATION_STEP = 15           # QIM step size — larger = more robust, more artifact
L3_BLOCKS_PER_BIT = 6               # Number of blocks encoding each single bit
L3_FRAME_INTERVAL = 3               # Watermark every Nth frame (3 = every 3rd)
L3_MIN_FRAME_AGREEMENT = 0.45       # Min fraction of frames agreeing on each bit

# ---- Fusion Decision ----
FUSION_MIN_AGREEING_LAYERS = 2      # Require at least 2 layers to agree
FUSION_OVERALL_THRESHOLD = 0.45     # Min fused confidence to report attribution
LAYER_AGREEMENT_THRESHOLDS = {
    "layer1": 0.35,                  # Min confidence for a layer to "agree"
    "layer2": 0.40,
    "layer3": 0.35,
}

# ---- Paths ----
REGISTRY_PATH = "session_registry.json"
DEMO_VIDEOS_DIR = "demo_videos"
WATERMARKED_DIR = "watermarked_outputs"
TEMP_DIR = "temp_processing"

# ---- Server ----
HOST = "0.0.0.0"
PORT = 8001   # 8001 so it runs alongside Module 1 (port 8000)
```

---

## 5. Module-by-Module Build Order

Build in this exact order. At each checkpoint you have a working, testable system.

### Checkpoint 1: Skeleton + registry (30 min)
1. Create folder structure
2. Write `requirements.txt` and `config.py`
3. Write `session_registry.py` — JSON-backed session store
4. Write minimal `app.py` with stub `/api/embed` and `/api/extract` endpoints
5. Write minimal `static/index.html` with two upload panels
6. Copy `attack_generator.py` from Module 1 into this folder
7. Create `watermarked_outputs/` and `temp_processing/` directories
8. **Verify:** `uvicorn app:app --port 8001 --reload` starts, page loads

### Checkpoint 2: Common utilities (45 min)
1. Write `watermark/common.py`:
   - Reed-Solomon encode/decode
   - HMAC-SHA256 key-based position generation
   - FFmpeg frame extraction
   - FFmpeg video reassembly
   - FFmpeg audio extraction and merging
   - ffprobe FPS and duration detection
2. Write a quick test in the Python REPL:
   ```python
   from watermark.common import rs_encode, rs_decode
   bits = rs_encode(123456789)
   result = rs_decode(bits)
   assert result == 123456789
   ```
3. **Verify:** RS encode → decode roundtrip works correctly

### Checkpoint 3: Layer 1 end-to-end (2.5 hours)
1. Write `watermark/layer1_visual.py` — spread spectrum embed + extract
2. Test the per-frame functions first with a single frame:
   ```python
   import cv2, numpy as np
   from watermark.layer1_visual import embed_frame, extract_frame
   from watermark.common import rs_encode
   frame = cv2.imread("demo_videos/attacks/test_frame.jpg")
   bits = rs_encode(999999)
   watermarked = embed_frame(frame.copy(), bits, frame_number=0)
   correlations = extract_frame(watermarked, len(bits), frame_number=0)
   # Check: positive correlations for bit=1, negative for bit=0
   ```
3. Then test the full video pipeline:
   ```python
   from watermark.layer1_visual import embed_video, extract_video
   embed_video("demo_videos/normalized_source_01.mp4", 999999, "test_l1.mp4")
   result = extract_video("test_l1.mp4")
   assert result["session_id_int"] == 999999
   ```
4. Test against an attacked version:
   ```python
   # Run attack_generator on test_l1.mp4 first
   result = extract_video("demo_videos/attacks/test_l1_03_recolored.mp4")
   # Should still recover 999999
   ```
5. **Verify:** Layer 1 roundtrip works. Check which attacks it survives.

### Checkpoint 4: Layer 2 end-to-end (2 hours)
1. Write `watermark/layer2_audio.py` — BPSK embed + extract
2. Test audio-only functions first:
   ```python
   import numpy as np, soundfile as sf
   from watermark.layer2_audio import embed_audio, extract_audio_watermark
   from watermark.common import rs_encode
   samples, sr = sf.read("test_audio.wav")
   bits = rs_encode(999999)
   watermarked = embed_audio(samples, sr, bits)
   result = extract_audio_watermark(watermarked, sr, len(bits))
   assert result["session_id_int"] == 999999
   ```
3. Test full video pipeline
4. Test with the muted attack — Layer 2 should return confidence=0 cleanly, no crash
5. **Verify:** Layer 2 survives re-encoding and format conversion. Fails gracefully on muted clips.

### Checkpoint 5: Layer 3 end-to-end (2 hours)
1. Write `watermark/layer3_dct.py` — DCT QIM embed + extract
2. Test per-frame DCT embed/extract first
3. Test full video pipeline
4. Specifically test against the CROPPED attack (which should defeat Layer 1 but not Layer 3)
5. **Verify:** Layer 3 survives cropping and resizing. This is its specific strength.

### Checkpoint 6: Full pipeline + fusion (1 hour)
1. Write `watermark/embedder.py` — orchestrate all 3 layers sequentially
2. Write `watermark/extractor.py` — orchestrate all 3 extractions + fusion
3. Wire both into FastAPI `/api/embed` and `/api/extract`
4. Create 3 watermarked viewer copies:
   - Viewer A: ID = generated UUID
   - Viewer B: ID = generated UUID
   - Viewer C: ID = generated UUID
5. Run `attack_generator.py --all` on Viewer B's copy
6. Run extraction on all 8 attack types
7. **Verify:** at least 6 of 8 attacks return the correct session ID (Viewer B)
8. **Verify:** Viewer A and Viewer C clips correctly return their own session IDs

### Checkpoint 7: UI + demo polish (1 hour)
1. Finish `static/index.html` — embed panel, extract panel, session registry list
2. Style result card: green for ATTRIBUTED, yellow for PARTIAL, red for NOT ATTRIBUTED
3. Add per-layer confidence bars
4. Add processing spinner (embedding takes 10-60 seconds depending on video length)
5. Run the full demo flow 3 times on stage-ready hardware
6. Tune thresholds in `config.py` if needed

---

## 6. Detailed Specs — Module by Module

### 6.1 `session_registry.py`

```python
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import config

class SessionRegistry:
    """
    JSON-backed registry of watermarking sessions.

    Each session entry:
    {
        "session_id_hex": "a1b2c3d4e5f6a7b8",   # 16 hex chars = 64 bits
        "session_id_int": 11671527838978859960,   # integer form for math
        "viewer_name": "Viewer B - ESPN US",
        "account_id": "user_9283@espn.com",
        "region": "United States",
        "platform": "Smart TV",
        "ip_address": "192.168.x.x",
        "timestamp": "2024-03-15T20:47:13Z",
        "source_video": "normalized_source_01.mp4",
        "watermarked_file": "watermarked_outputs/viewerB_source01.mp4",
        "layers_embedded": ["layer1", "layer2", "layer3"],
        "module1_fingerprint": null
    }
    """

    def __init__(self):
        self.sessions: dict[str, dict] = {}  # session_id_hex -> entry
        self._load()

    def create_session(self,
                       viewer_name: str,
                       source_video: str,
                       account_id: str = "",
                       region: str = "",
                       platform: str = "",
                       ip_address: str = "") -> dict:
        """
        Generate a new session ID and register it.

        Session ID generation:
        1. Generate uuid4()
        2. Take the first 16 hex characters (= 64 bits exactly)
        3. Convert to int: session_id_int = int(hex_str, 16)
        4. Store all metadata with current UTC timestamp
        5. Save to JSON

        Returns the complete session entry dict.
        """

    def lookup_by_int(self, session_id_int: int) -> dict | None:
        """
        Look up a session by its integer form.
        Convert int to hex, then look up.
        Return None if not found.
        """

    def lookup_by_hex(self, session_id_hex: str) -> dict | None:
        """Look up by hex string. Return None if not found."""

    def update_watermarked_file(self, session_id_hex: str,
                                 filepath: str,
                                 layers: list[str]) -> None:
        """
        Update an existing session with the watermarked output file path
        and which layers were successfully embedded.
        Called after embedding completes.
        """

    def list_sessions(self) -> list[dict]:
        """Return all sessions sorted by timestamp descending."""

    def _save(self):
        """
        Write to JSON file atomically.
        Write to temp file first, then rename to avoid corruption
        if the process is killed mid-write.
        """
        temp = Path(config.REGISTRY_PATH + ".tmp")
        data = list(self.sessions.values())
        temp.write_text(json.dumps(data, indent=2, default=str))
        temp.replace(config.REGISTRY_PATH)

    def _load(self):
        """Load from JSON file if it exists. Silent if missing."""
        path = Path(config.REGISTRY_PATH)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        self.sessions = {e["session_id_hex"]: e for e in data}

    def reset(self):
        """Clear all sessions and delete the JSON file."""
```

### 6.2 `watermark/common.py` — Shared Utilities

```python
import hashlib
import hmac
import numpy as np
import subprocess
import shutil
from pathlib import Path
from reedsolo import RSCodec, ReedSolomonError
import config

# ---- Reed-Solomon Error Correction ----

_rs = RSCodec(config.RS_ERROR_CORRECTION_SYMBOLS)

def rs_encode(session_id_int: int) -> list[int]:
    """
    Encode a 64-bit integer with Reed-Solomon error correction.
    Returns a flat list of bits (0s and 1s).

    Steps:
    1. Convert session_id_int to bytes:
       data_bytes = session_id_int.to_bytes(config.SESSION_ID_BYTES, 'big')
    2. RS encode: encoded_bytes = _rs.encode(data_bytes)
       This produces SESSION_ID_BYTES + RS_ERROR_CORRECTION_SYMBOLS bytes
    3. Convert all bytes to bits:
       bits = []
       for byte in encoded_bytes:
           for i in range(7, -1, -1):  # MSB first
               bits.append((byte >> i) & 1)
    4. Return bits list

    Example: 8 data bytes + 10 RS bytes = 18 bytes = 144 bits to embed
    """

def rs_decode(bits: list[int]) -> int | None:
    """
    Decode RS-protected bits back to the original integer.
    Returns None if corruption exceeds RS capacity.

    Steps:
    1. Convert bits to bytes:
       Pack every 8 bits into one byte
       If len(bits) not divisible by 8, pad with 0s
    2. RS decode: decoded_bytes, _, _ = _rs.decode(encoded_bytes)
    3. Convert to int: result = int.from_bytes(decoded_bytes, 'big')
    4. Return result

    Wrap step 2 in try/except ReedSolomonError:
    If RS capacity exceeded, return None (not crashable)
    """

# ---- HMAC-Based Key Derivation for Position Generation ----

def _get_rng(frame_number: int) -> np.random.RandomState:
    """
    Generate a deterministic RandomState seeded by HMAC-SHA256.

    seed_bytes = HMAC-SHA256(
        key=config.WATERMARK_SECRET_KEY.encode(),
        msg=f"{config.WATERMARK_SALT}:{frame_number}".encode()
    )
    seed_int = int.from_bytes(seed_bytes[:4], 'big')
    return np.random.RandomState(seed_int)

    CRITICAL: This must return the SAME rng for the same frame_number.
    Same seed = same sequence. This is what makes embed and extract
    use the same positions.
    """

def get_block_positions(frame_number: int, num_bits: int,
                        frame_h: int, frame_w: int,
                        block_size: int) -> list[tuple[int, int]]:
    """
    Get a list of (row, col) top-left corners for watermark blocks.
    One block position per bit.

    Algorithm:
    1. Compute grid dimensions:
       rows_in_grid = frame_h // block_size
       cols_in_grid = frame_w // block_size
       total_blocks = rows_in_grid * cols_in_grid
    2. Get RNG via _get_rng(frame_number)
    3. Sample num_bits unique indices from [0, total_blocks)
    4. Convert each index to (row, col) in grid:
       grid_row = idx // cols_in_grid
       grid_col = idx % cols_in_grid
    5. Convert grid position to pixel position:
       pixel_row = grid_row * block_size
       pixel_col = grid_col * block_size
    6. Return list of (pixel_row, pixel_col) tuples

    If num_bits > total_blocks (video too small): raise ValueError with
    a clear message like "Video resolution too small for watermarking.
    Need at least {num_bits * block_size * block_size} pixels."
    """

def get_noise_pattern(frame_number: int, bit_index: int,
                      block_size: int) -> np.ndarray:
    """
    Generate a bipolar {-1, +1} noise pattern for one block.

    Use a seed derived from both frame_number AND bit_index so
    each bit in each frame has a unique noise pattern:
    msg = f"{config.WATERMARK_SALT}:{frame_number}:{bit_index}"
    seed_bytes = HMAC-SHA256(key, msg.encode())
    seed_int = int.from_bytes(seed_bytes[:4], 'big')
    rng = np.random.RandomState(seed_int)
    noise = rng.choice([-1.0, 1.0], size=(block_size, block_size))
    return noise
    """

# ---- FFmpeg Utilities ----

def get_fps(video_path: str) -> float:
    """
    Get video FPS using ffprobe.

    Command:
      ffprobe -v error -select_streams v:0
              -show_entries stream=r_frame_rate
              -of default=noprint_wrappers=1:nokey=1
              <video_path>

    Output is a fraction like "30/1" or "25/1" or "2997/100".
    Parse: num, den = output.split("/")
    Return: float(num) / float(den)

    If ffprobe fails, return 30.0 as a safe default.
    """

def get_duration(video_path: str) -> float:
    """
    Get video duration in seconds using ffprobe.

    Command:
      ffprobe -v error -show_entries format=duration
              -of default=noprint_wrappers=1:nokey=1
              <video_path>

    If fails, return 0.0.
    """

def extract_frames(video_path: str, output_dir: str) -> list[tuple[int, str]]:
    """
    Extract ALL frames from a video as PNG files (lossless).

    Command:
      ffmpeg -i <video_path> -q:v 1 <output_dir>/frame_%06d.png

    Use PNG specifically — not JPG. JPG compression would corrupt
    the spread-spectrum signal (Layer 1) before we even start.

    Returns list of (frame_index_1based, filepath) tuples.
    frame_index is 1-based because FFmpeg numbers from 1.

    Raise RuntimeError if FFmpeg returns nonzero exit code.
    Always wrap in try/finally to clean up on error.
    """

def reassemble_video(frames_dir: str, original_video: str,
                     output_path: str) -> None:
    """
    Reassemble PNG frames back into a video with original audio.

    Two-step process:
    STEP 1 — Frames to silent video:
      fps = get_fps(original_video)
      ffmpeg -framerate <fps> -i <frames_dir>/frame_%06d.png
             -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p
             <temp_silent.mp4>

    STEP 2 — Add original audio:
      ffmpeg -i <temp_silent.mp4> -i <original_video>
             -c:v copy -c:a aac -b:a 192k
             -map 0:v:0 -map 1:a:0? -shortest
             <output_path>

    The -map 1:a:0? with the "?" means: use original audio if it exists,
    produce video-only output if not. This handles muted source videos.

    Clean up temp_silent.mp4 after step 2.
    Raise RuntimeError if either FFmpeg step fails.
    """

def extract_audio(video_path: str, output_wav: str) -> bool:
    """
    Extract audio as 44.1kHz mono WAV.

    Command:
      ffmpeg -i <video_path> -vn -acodec pcm_s16le
             -ar 44100 -ac 1 <output_wav>

    Returns True if audio was extracted successfully.
    Returns False if the video has no audio track.

    Detect "no audio" by checking ffprobe output for audio streams,
    OR by checking if the output file is 0 bytes after ffmpeg runs.
    Do NOT crash on missing audio — return False gracefully.
    """

def replace_audio(video_path: str, audio_wav: str,
                  output_path: str) -> None:
    """
    Replace the audio track of a video with a new WAV file.

    Command:
      ffmpeg -i <video_path> -i <audio_wav>
             -c:v copy -c:a aac -b:a 192k
             -map 0:v:0 -map 1:a:0 -shortest
             <output_path>

    Raise RuntimeError if FFmpeg fails.
    """

def run_ffmpeg(args: list[str], description: str = "") -> None:
    """
    Run an FFmpeg command. Raise RuntimeError with context if it fails.

    Implementation:
    result = subprocess.run(
        ["ffmpeg"] + args,
        capture_output=True, text=True, shell=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed ({description}): {result.stderr[-500:]}"
        )
    """
```

### 6.3 `watermark/layer1_visual.py` — Spread Spectrum Visual Watermark

```python
import numpy as np
import cv2
from pathlib import Path
import tempfile, shutil
from watermark.common import (
    rs_encode, rs_decode,
    get_block_positions, get_noise_pattern,
    extract_frames, reassemble_video,
    get_fps
)
import config

def embed_frame(frame_bgr: np.ndarray, bits: list[int],
                frame_number: int) -> np.ndarray:
    """
    Embed watermark bits into one frame using spread spectrum.

    The frame is modified in-place conceptually, but we return a copy.

    Algorithm:
    1. frame_f = frame_bgr.astype(np.float32)
    2. Get block positions: positions = get_block_positions(
           frame_number, len(bits),
           frame_f.shape[0], frame_f.shape[1],
           config.L1_BLOCK_SIZE)
    3. For each bit i:
       row, col = positions[i]
       noise = get_noise_pattern(frame_number, i, config.L1_BLOCK_SIZE)
       # Apply to all 3 color channels equally:
       for channel in range(3):
           block = frame_f[row:row+bs, col:col+bs, channel]
           if bits[i] == 1:
               block += noise * config.L1_NOISE_STRENGTH
           else:
               block -= noise * config.L1_NOISE_STRENGTH
           # clip:
           frame_f[row:row+bs, col:col+bs, channel] = np.clip(block, 0, 255)
    4. Return frame_f.astype(np.uint8)

    bs = config.L1_BLOCK_SIZE
    """

def extract_frame(frame_bgr: np.ndarray, num_bits: int,
                  frame_number: int) -> list[float]:
    """
    Extract correlation values from one frame.
    Returns a list of num_bits floats.
    Positive float → likely bit 1. Negative → likely bit 0.
    Magnitude indicates confidence.

    Algorithm:
    1. frame_f = frame_bgr.astype(np.float32)
    2. Get same block positions (same frame_number = same positions)
    3. For each bit i:
       row, col = positions[i]
       noise = get_noise_pattern(frame_number, i, config.L1_BLOCK_SIZE)
       # Average correlation across 3 channels:
       corr = 0.0
       for channel in range(3):
           block = frame_f[row:row+bs, col:col+bs, channel]
           # Normalize block to zero mean for cleaner correlation:
           block_norm = block - block.mean()
           corr += np.mean(block_norm * noise)
       corr /= 3.0
       correlations.append(corr / config.L1_NOISE_STRENGTH)
    4. Return correlations list

    The division by L1_NOISE_STRENGTH normalizes the magnitude so
    confidence scores are comparable across different noise strengths.
    """

def embed_video(video_path: str, session_id_int: int,
                output_path: str) -> dict:
    """
    Embed Layer 1 watermark throughout a video.

    Full flow:
    1. bits = rs_encode(session_id_int)
    2. tmp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
    3. frames = extract_frames(video_path, tmp_dir)
       (returns all frames as PNG files)
    4. For each frame at index i:
       - Load frame: cv2.imread(filepath)
       - If i % config.L1_FRAME_INTERVAL == 0:
           watermarked = embed_frame(frame, bits, frame_number=i)
           cv2.imwrite(filepath, watermarked)
         Else: leave frame unchanged
    5. reassemble_video(tmp_dir, video_path, output_path)
       (copies audio from original video)
    6. shutil.rmtree(tmp_dir)  # ALWAYS clean up, even on error
    7. Return:
       {
           "frames_total": len(frames),
           "frames_watermarked": count,
           "bits_embedded": len(bits),
       }

    CRITICAL:
    - Use try/finally to ensure tmp_dir is always cleaned up
    - If any frame fails to process, log and skip it (don't abort)
    - Use cv2.imread(..., cv2.IMREAD_COLOR) explicitly
    """

def extract_video(video_path: str) -> dict:
    """
    Extract Layer 1 watermark from a video.

    Full flow:
    1. Determine expected number of bits:
       num_bits = (config.SESSION_ID_BYTES + config.RS_ERROR_CORRECTION_SYMBOLS) * 8
    2. tmp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
    3. frames = extract_frames(video_path, tmp_dir)
    4. For each frame at index i where i % config.L1_FRAME_INTERVAL == 0:
       - Load frame
       - correlations = extract_frame(frame, num_bits, frame_number=i)
       - all_correlations.append(correlations)  # shape: [num_frames, num_bits]
    5. If no frames were processed → return {"confidence": 0, "session_id_int": None}
    6. Aggregate across frames:
       avg_correlations = np.mean(all_correlations, axis=0)  # shape: [num_bits]
       # For each bit, determine value and confidence:
       bits = []
       reliabilities = []
       for corr in avg_correlations:
           if abs(corr) >= config.L1_CORRELATION_THRESHOLD:
               bits.append(1 if corr > 0 else 0)
               reliabilities.append(abs(corr))
           else:
               bits.append(-1)   # uncertain
               reliabilities.append(0.0)
       # Count reliable bits:
       reliable_count = sum(1 for b in bits if b != -1)
       reliable_fraction = reliable_count / num_bits
       # Replace uncertain bits with best guess (sign of average correlation):
       clean_bits = [1 if corr >= 0 else 0 for corr in avg_correlations]
    7. session_id_int = rs_decode(clean_bits)
    8. shutil.rmtree(tmp_dir)
    9. Return:
       {
           "session_id_int": session_id_int,  # None if RS decode failed
           "session_id_hex": hex(session_id_int)[2:] if session_id_int else None,
           "confidence": reliable_fraction,
           "frames_analyzed": count,
           "bits_total": num_bits,
           "bits_reliable": reliable_count,
       }
    """
```

### 6.4 `watermark/layer2_audio.py` — BPSK Audio Watermark

```python
import numpy as np
from scipy import signal as scipy_signal
import soundfile as sf
from pathlib import Path
import tempfile, shutil
from watermark.common import (
    rs_encode, rs_decode,
    extract_audio, replace_audio
)
import config

def _generate_tone(bit_value: int, duration_samples: int,
                   sample_rate: int, amplitude: float) -> np.ndarray:
    """
    Generate a single BPSK tone burst.

    t = np.linspace(0, duration_samples/sample_rate,
                    duration_samples, endpoint=False)
    carrier = np.sin(2 * np.pi * config.L2_CARRIER_FREQ * t)
    if bit_value == 1:
        return carrier * amplitude   # 0° phase
    else:
        return -carrier * amplitude  # 180° phase (inverted = BPSK)
    """

def embed_audio(samples: np.ndarray, sample_rate: int,
                bits: list[int]) -> np.ndarray:
    """
    Embed watermark bits as BPSK tones into audio samples.

    samples: 1D numpy array of float64, range [-1, 1]
    Returns modified samples (same shape).

    Algorithm:
    1. Compute duration per bit in samples:
       bit_samples = int(config.L2_BIT_DURATION_MS / 1000 * sample_rate)
    2. Compute total duration of one full bit sequence:
       seq_samples = len(bits) * bit_samples
    3. Compute how many full repetitions fit in the audio:
       repeats = int(len(samples) / (config.L2_REPEAT_INTERVAL_SEC * sample_rate))
       repeats = max(1, repeats)  # at least one attempt
    4. modified = samples.copy()
    5. For each repetition r:
       start_sample = r * int(config.L2_REPEAT_INTERVAL_SEC * sample_rate)
       For each bit i:
           bit_start = start_sample + i * bit_samples
           bit_end   = bit_start + bit_samples
           if bit_end > len(modified):
               break  # ran out of audio
           tone = _generate_tone(bits[i], bit_samples, sample_rate,
                                  config.L2_AMPLITUDE)
           modified[bit_start:bit_end] += tone
    6. Clip to [-1.0, 1.0] to prevent clipping artifacts
    7. Return modified

    IMPORTANT: Make sure the audio array is 1D (mono) before processing.
    If it's 2D (stereo), take the first channel only:
    if samples.ndim > 1:
        samples = samples[:, 0]
    """

def extract_audio_watermark(samples: np.ndarray, sample_rate: int,
                              num_bits: int) -> dict:
    """
    Extract BPSK watermark from audio samples.

    Algorithm:
    1. Ensure 1D mono
    2. Early exit: check energy in the carrier band.
       If near-zero, no watermark present (muted/replaced audio):
       # Rough check: bandpass filter, check RMS
       If RMS < 1e-6: return {"confidence": 0, "session_id_int": None}
    3. Bandpass filter to isolate carrier frequency:
       sos = scipy_signal.butter(
           4,
           [config.L2_BANDPASS_LOW, config.L2_BANDPASS_HIGH],
           btype='bandpass',
           fs=sample_rate,
           output='sos'
       )
       filtered = scipy_signal.sosfiltfilt(sos, samples)
    4. Generate reference carrier (same frequency, 0° phase):
       bit_samples = int(config.L2_BIT_DURATION_MS / 1000 * sample_rate)
    5. For each repetition window:
       start = r * int(config.L2_REPEAT_INTERVAL_SEC * sample_rate)
       For each bit i:
           bit_start = start + i * bit_samples
           bit_end = bit_start + bit_samples
           if bit_end > len(filtered): break
           segment = filtered[bit_start:bit_end]
           # Generate reference tone at 0° phase:
           t = np.linspace(0, bit_samples/sample_rate, bit_samples, endpoint=False)
           ref = np.sin(2 * np.pi * config.L2_CARRIER_FREQ * t)
           # Cross-correlation at zero lag:
           corr = np.mean(segment * ref)
           all_correlations[i].append(corr)
    6. Average correlations across repetitions for each bit:
       For each bit i:
           avg_corr = np.mean(all_correlations[i])
           if avg_corr > config.L2_PHASE_DETECTION_THRESHOLD:
               bit = 1
           elif avg_corr < -config.L2_PHASE_DETECTION_THRESHOLD:
               bit = 0
           else:
               bit = -1  # uncertain
    7. rs_decode the bits
    8. Return results dict matching Layer 1 format

    Returns:
    {
        "session_id_int": int or None,
        "session_id_hex": str or None,
        "confidence": float,
        "repetitions_analyzed": int,
        "bits_total": int,
        "bits_reliable": int,
    }
    """

def embed_video(video_path: str, session_id_int: int,
                output_path: str) -> dict:
    """
    Embed Layer 2 audio watermark in a video.

    Flow:
    1. tmp_audio = tempfile path for extracted audio
    2. has_audio = extract_audio(video_path, tmp_audio)
    3. If not has_audio:
       - Copy video unchanged to output_path
       - Return {"status": "no_audio", "confidence_expected": 0}
    4. samples, sr = soundfile.read(tmp_audio)
    5. bits = rs_encode(session_id_int)
    6. watermarked_samples = embed_audio(samples, sr, bits)
    7. Write watermarked_samples back to tmp_audio (overwrite)
    8. replace_audio(video_path, tmp_audio, output_path)
    9. Clean up tmp_audio
    10. Return {"status": "ok", "bits_embedded": len(bits)}

    NOTE: The input video_path here is the output of Layer 1 embedding.
    The output goes to output_path.
    """

def extract_video(video_path: str) -> dict:
    """
    Extract Layer 2 audio watermark from a video.

    Flow:
    1. tmp_audio = temp path
    2. has_audio = extract_audio(video_path, tmp_audio)
    3. If not has_audio:
       return {"confidence": 0.0, "session_id_int": None,
               "session_id_hex": None, "status": "no_audio"}
    4. samples, sr = soundfile.read(tmp_audio)
    5. num_bits = (SESSION_ID_BYTES + RS_ERROR_CORRECTION_SYMBOLS) * 8
    6. result = extract_audio_watermark(samples, sr, num_bits)
    7. Clean up tmp_audio
    8. Return result
    """
```

### 6.5 `watermark/layer3_dct.py` — DCT Structural Watermark

```python
import numpy as np
import cv2
from pathlib import Path
import tempfile, shutil
from watermark.common import (
    rs_encode, rs_decode,
    get_block_positions, _get_rng,
    extract_frames, reassemble_video
)
import config

def _get_dct_block_positions(frame_number: int, num_bits: int,
                              frame_h: int, frame_w: int) -> list[list[tuple]]:
    """
    For each bit, get L3_BLOCKS_PER_BIT block positions.

    Returns a list of lists:
    [
        [(r0,c0), (r1,c1), ...],  # blocks for bit 0
        [(r0,c0), (r1,c1), ...],  # blocks for bit 1
        ...
    ]

    Each block is at an (row, col) that is a multiple of 8 (DCT block size).
    Use _get_rng(frame_number) as the random source for block selection.
    Total blocks needed = num_bits * L3_BLOCKS_PER_BIT
    Grid: (frame_h // 8) * (frame_w // 8) available positions
    Sample without replacement.
    """

def embed_frame_dct(frame_bgr: np.ndarray, bits: list[int],
                    frame_number: int) -> np.ndarray:
    """
    Embed watermark bits using DCT Quantization Index Modulation.

    Algorithm:
    1. Convert BGR to YCrCb: ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    2. Extract Y (luminance) channel: y_channel = ycrcb[:,:,0].astype(np.float32)
    3. Get block positions for all bits
    4. For each bit i and each of its L3_BLOCKS_PER_BIT blocks at (r, c):
       a. Extract 8x8 block: block = y_channel[r:r+8, c:c+8]
       b. Compute DCT: dct_block = cv2.dct(block)
       c. Get target coefficient: coeff = dct_block[L3_TARGET_COEFF[0], L3_TARGET_COEFF[1]]
       d. Apply QIM (Quantization Index Modulation):
          q = config.L3_QUANTIZATION_STEP
          n = round(coeff / q)      # which quantization level
          if bits[i] == 1:
              if n % 2 == 0:         # even → shift to nearest odd
                  n += 1
          else:  # bits[i] == 0
              if n % 2 != 0:         # odd → shift to nearest even
                  n += 1
          new_coeff = n * q
          dct_block[L3_TARGET_COEFF[0], L3_TARGET_COEFF[1]] = new_coeff
       e. Inverse DCT: restored = cv2.idct(dct_block)
       f. Put block back: y_channel[r:r+8, c:c+8] = restored
    5. Clip Y channel to [0, 255]
    6. Put Y back: ycrcb[:,:,0] = y_channel.astype(np.uint8)
    7. Convert back: result = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    8. Return result

    WHY YCrCb: Modifying only the luminance (Y) channel is less visible
    than modifying all channels. Color perception is less sensitive than
    brightness perception.
    """

def extract_frame_dct(frame_bgr: np.ndarray, num_bits: int,
                      frame_number: int) -> list[float]:
    """
    Extract DCT watermark from one frame.

    Returns list of floats:
    Positive → bit likely 1 (coefficient at ODD multiple)
    Negative → bit likely 0 (coefficient at EVEN multiple)
    Magnitude → confidence (fraction of blocks agreeing)

    Algorithm:
    1. Convert to YCrCb, extract Y as float32
    2. Get block positions
    3. For each bit i:
       votes = []
       For each block (r, c) for bit i:
           block = y_channel[r:r+8, c:c+8]
           dct_block = cv2.dct(block)
           coeff = dct_block[L3_TARGET_COEFF[0], L3_TARGET_COEFF[1]]
           q = config.L3_QUANTIZATION_STEP
           n = round(coeff / q)
           # n odd → vote for 1, n even → vote for 0
           votes.append(1.0 if n % 2 != 0 else -1.0)
       # Aggregate: mean of votes
       # +1.0 = all blocks say bit 1, -1.0 = all blocks say bit 0
       # 0.0 = split (uncertain)
       confidence = np.mean(votes)
       correlations.append(confidence)
    4. Return correlations
    """

def embed_video(video_path: str, session_id_int: int,
                output_path: str) -> dict:
    """
    Embed Layer 3 DCT watermark throughout a video.

    Same structure as Layer 1's embed_video:
    1. RS-encode session ID → bits
    2. Extract all frames to temp dir
    3. For every L3_FRAME_INTERVAL-th frame:
       - Load frame
       - watermarked = embed_frame_dct(frame, bits, frame_number)
       - Save back
    4. Reassemble video
    5. Clean up temp dir
    6. Return stats dict
    """

def extract_video(video_path: str) -> dict:
    """
    Extract Layer 3 DCT watermark from a video.

    Same structure as Layer 1's extract_video:
    1. Extract all frames
    2. For every L3_FRAME_INTERVAL-th frame:
       - correlations = extract_frame_dct(frame, num_bits, frame_number)
       - Collect correlations
    3. Average across frames
    4. Threshold correlations to bits
    5. RS-decode
    6. Return results dict
    """
```

### 6.6 `watermark/embedder.py` — Full 3-Layer Embedding Pipeline

```python
import shutil
from pathlib import Path
import time
from watermark import layer1_visual, layer2_audio, layer3_dct
from session_registry import SessionRegistry
import config

def embed_full(video_path: str,
               viewer_name: str,
               registry: SessionRegistry,
               account_id: str = "",
               region: str = "",
               platform: str = "",
               ip_address: str = "") -> dict:
    """
    Embed all 3 watermark layers sequentially.

    Flow:
    1. session = registry.create_session(viewer_name, ...)
       session_id_int = session["session_id_int"]

    2. Set up output paths:
       source_stem = Path(video_path).stem  # e.g. "normalized_source_01"
       viewer_slug = viewer_name.lower().replace(" ", "_")[:20]
       output_filename = f"{viewer_slug}_{source_stem}.mp4"
       output_path = Path(config.WATERMARKED_DIR) / output_filename

    3. Layer 1 embedding:
       tmp1 = Path(config.TEMP_DIR) / f"tmp_l1_{session_id_hex}.mp4"
       l1_result = layer1_visual.embed_video(video_path, session_id_int, str(tmp1))
       layers_embedded = ["layer1"]

    4. Layer 2 embedding (input = Layer 1 output):
       tmp2 = Path(config.TEMP_DIR) / f"tmp_l2_{session_id_hex}.mp4"
       l2_result = layer2_audio.embed_video(str(tmp1), session_id_int, str(tmp2))
       layers_embedded.append("layer2")

    5. Layer 3 embedding (input = Layer 2 output):
       layer3_dct.embed_video(str(tmp2), session_id_int, str(output_path))
       layers_embedded.append("layer3")

    6. Clean up intermediate temp files (tmp1, tmp2)

    7. registry.update_watermarked_file(session["session_id_hex"],
                                         str(output_path), layers_embedded)

    8. Return:
       {
           "session_id_hex": session["session_id_hex"],
           "session_id_int": session_id_int,
           "viewer_name": viewer_name,
           "output_path": str(output_path),
           "output_filename": output_filename,
           "layers_embedded": layers_embedded,
           "processing_seconds": elapsed,
       }

    CRITICAL ERROR HANDLING:
    - If Layer 1 fails: log error, try to continue with Layer 2 using
      the original video as input. Mark layer1 as failed.
    - If Layer 2 fails: log error, continue with Layer 3.
    - If Layer 3 fails: log error, use the best available output.
    - If ALL layers fail: return error dict, do NOT crash server.
    - ALWAYS clean up temp files in a finally block.
    - ALWAYS create the session in the registry FIRST so it exists
      even if embedding fails. Better to have a session with no output
      than to lose the session ID entirely.
    """
```

### 6.7 `watermark/extractor.py` — Full 3-Layer Extraction + Fusion

```python
from watermark import layer1_visual, layer2_audio, layer3_dct
from session_registry import SessionRegistry
import config

def extract_full(video_path: str, registry: SessionRegistry) -> dict:
    """
    Extract watermarks from all 3 layers and fuse results.

    Flow:
    1. Run all 3 extractors:
       l1 = layer1_visual.extract_video(video_path)
       l2 = layer2_audio.extract_video(video_path)
       l3 = layer3_dct.extract_video(video_path)

    2. For each layer result that has a session_id_int:
       - Look it up in the registry
       - If found → this layer "votes" for that session ID
       - If not found → session ID is invalid (random noise decode)
         → set layer confidence to 0, session_id = None

    3. Build candidate votes:
       votes = {}  # session_id_hex → {"count": N, "layers": [...], "confidences": [...]}
       For each layer result:
           if session_id_hex and found_in_registry:
               votes[session_id_hex]["count"] += 1
               votes[session_id_hex]["confidences"].append(confidence)
               votes[session_id_hex]["layers"].append("layer1/2/3")

    4. Pick the winner (most votes):
       winner = max(votes, key=lambda k: votes[k]["count"])
       winner_data = votes[winner]

    5. Apply decision rules:
       - "ATTRIBUTED" if:
           winner_data["count"] >= config.FUSION_MIN_AGREEING_LAYERS
           AND all contributing layer confidences >= LAYER_AGREEMENT_THRESHOLDS
           AND overall_confidence >= config.FUSION_OVERALL_THRESHOLD
       - "PARTIAL" if:
           winner_data["count"] == 1 only
       - "NOT ATTRIBUTED" if:
           no layer found any valid session ID

    6. If ATTRIBUTED or PARTIAL: look up full session from registry

    7. Build explanation string:
       - Which layers agreed, which failed, and why (muted=L2 expected fail, etc.)
       - "Layers 1 and 3 agree on Viewer B (ESPN US). Layer 2 failed —
          audio was stripped in this clip. Attribution confirmed."

    8. Return:
       {
           "verdict": "ATTRIBUTED" | "PARTIAL" | "NOT ATTRIBUTED",
           "session_id_hex": str or None,
           "viewer_name": str or None,
           "session_details": {full registry entry} or None,
           "overall_confidence": float,  # avg of agreeing layer confidences
           "agreeing_layers": int,
           "per_layer": {
               "layer1": {
                   "session_id_hex": str or None,
                   "confidence": float,
                   "status": "match" | "no_match" | "no_audio" | "failed",
               },
               "layer2": { ... },
               "layer3": { ... },
           },
           "explanation": str,
       }

    EXPLANATION BUILDER RULES:
    Build the explanation string dynamically based on actual results:
    - If a layer matched: "Layer 1 (Visual): matched Viewer B [85% confidence]"
    - If muted (L2 confidence=0 due to no audio): "Layer 2 (Audio): skipped — audio track removed"
    - If L1 failed heavy crop: "Layer 1 (Visual): uncertain — likely heavy crop attack"
    - If all 3 agree: "All 3 layers confirm Viewer B. High confidence attribution."
    - If 2 of 3 agree: "2 of 3 layers confirm. [Layer X] could not extract due to [attack]."
    - If all disagree: "Layers returned different IDs — likely heavy re-encoding or this video was not watermarked."
    """
```

### 6.8 `app.py` — FastAPI Server

```python
"""
FastAPI server for Module 3.

Endpoints:
  GET  /                       → serve static/index.html
  GET  /api/sessions           → list all registered sessions
  POST /api/embed              → upload video + metadata → embed watermark → return result
  POST /api/extract            → upload suspect video → extract → return attribution
  GET  /api/download/{name}    → download a watermarked video file
  POST /api/reset              → clear registry + delete watermarked outputs

Key implementation details:

POST /api/embed:
  - Accept: multipart form with fields:
      file: video upload
      viewer_name: str (required)
      account_id: str (optional)
      region: str (optional)
      platform: str (optional, e.g. "Mobile App", "Smart TV", "Web")
  - Save upload to temp file in TEMP_DIR
  - Call: result = await asyncio.to_thread(embedder.embed_full, ...)
    (use asyncio.to_thread because embedding is CPU-bound and slow)
  - Delete temp upload
  - Return JSON: session info + download URL
  - Response includes: {
        "session_id_hex": "...",
        "viewer_name": "...",
        "download_url": "/api/download/viewerB_source01.mp4",
        "processing_seconds": 45.3,
        "layers_embedded": ["layer1", "layer2", "layer3"]
    }

POST /api/extract:
  - Accept: multipart form with field:
      file: suspect video upload
  - Save upload to temp file
  - Call: result = await asyncio.to_thread(extractor.extract_full, ...)
  - Delete temp file
  - Return full attribution result JSON

GET /api/download/{name}:
  - Serve file from WATERMARKED_DIR
  - Use fastapi.responses.FileResponse
  - Set Content-Disposition: attachment to force download
  - Return 404 if file not found

POST /api/reset:
  - registry.reset()
  - Delete all files in WATERMARKED_DIR
  - Return {"status": "ok"}

CORS: allow all origins (CORSMiddleware, allow_origins=["*"])
Error handling: every endpoint wrapped in try/except, return {"error": str(e)} on failure

On startup:
  - Create WATERMARKED_DIR and TEMP_DIR if they don't exist
  - Load session registry
"""
```

### 6.9 `static/index.html` — The UI

**Design:** Same dark theme as Module 1. Two panels side by side.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  HEADER: "Source Attribution Engine — Module 3"                          │
│  "WHO leaked it?"                                                        │
├──────────────────────────────────┬───────────────────────────────────────┤
│                                  │                                       │
│   📥 EMBED WATERMARK             │   🔍 EXTRACT & ATTRIBUTE              │
│                                  │                                       │
│   [Choose video from             │   [Choose suspect clip]               │
│    demo_videos/ ]                │                                       │
│                                  │   [Extract] button                    │
│   Viewer Name: [____________]    │                                       │
│   Account ID:  [____________]    │   ┌────────────────────────────────┐  │
│   Region:      [dropdown ▼  ]    │   │  ✅  ATTRIBUTED                │  │
│   Platform:    [dropdown ▼  ]    │   │                                │  │
│                                  │   │  Viewer: Viewer B – ESPN US    │  │
│   [Embed Watermark] button       │   │  Account: user@espn.com        │  │
│                                  │   │  Region: United States         │  │
│   [spinner / progress message]   │   │  Platform: Smart TV            │  │
│                                  │   │  Session: a1b2c3d4e5f6a7b8     │  │
│   ✅ Done! Processing: 42.1s     │   │  Watermarked: 20:47 UTC        │  │
│   📥 Download watermarked copy   │   │  Confidence: 82%               │  │
│                                  │   │                                │  │
│                                  │   │  Layer 1 Visual:  ████████ 85% │  │
│                                  │   │  Layer 2 Audio:   ░░░░░░░░  0% │  │
│                                  │   │    └ audio stripped by pirate  │  │
│                                  │   │  Layer 3 Struct:  ███████░ 79% │  │
│                                  │   │                                │  │
│                                  │   │  "Layers 1+3 agree. Audio      │  │
│                                  │   │   stripped — expected for      │  │
│                                  │   │   muted attack."               │  │
│                                  │   └────────────────────────────────┘  │
├──────────────────────────────────┴───────────────────────────────────────┤
│  SESSION REGISTRY                                                        │
│  a1b2c3d4 │ Viewer B – ESPN US    │ source_01.mp4 │ Smart TV  │ 20:47   │
│  e5f6g7h8 │ Viewer A – BBC UK     │ source_01.mp4 │ Mobile    │ 20:48   │
│  i9j0k1l2 │ Viewer C – Star India │ source_01.mp4 │ Web       │ 20:49   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key UI behaviors:**

1. **Embed panel:**
   - File input styled as a drop zone
   - Region dropdown: UK, US, India, Australia, Germany, Other
   - Platform dropdown: Mobile App, Smart TV, Web Browser, Desktop App, Other
   - On submit: disable button, show spinning indicator + message "Embedding 3 watermark layers... this takes ~30-60 seconds"
   - On complete: show green success card with download link
   - Session registry list auto-refreshes after each embed

2. **Extract panel:**
   - File input styled as a drop zone
   - On submit: disable button, show "Extracting watermarks from all 3 layers..."
   - On complete: show result card
   - Result card colors:
     - Green border + ✅: ATTRIBUTED (2+ layers agree)
     - Yellow border + ⚠️: PARTIAL (only 1 layer matched)
     - Red border + ❌: NOT ATTRIBUTED
   - Per-layer bars: show confidence % + short status note
   - Explanation text below the bars

3. **Session registry (bottom):**
   - Scrollable horizontal table
   - Shows: session ID (truncated), viewer name, source video, platform, timestamp
   - Clicking a row highlights it (for cross-referencing during demo)

4. **Dark theme CSS (same as Module 1):**
   ```css
   :root {
     --bg: #0a0a0f;
     --card: #111118;
     --border: #1e293b;
     --text: #e2e8f0;
     --muted: #94a3b8;
     --green: #22c55e;
     --yellow: #f59e0b;
     --red: #ef4444;
     --blue: #3b82f6;
   }
   ```

5. **No external CSS frameworks. No JavaScript frameworks.** Vanilla JS + vanilla CSS only. The whole UI is one HTML file.

---

## 7. `requirements.txt`

```
fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9
opencv-python>=4.9
numpy>=1.26
Pillow>=10.0
scipy>=1.12
soundfile>=0.12
reedsolo>=1.7
```

---

## 8. Demo Flow — Exactly What to Do On Stage

This is the precise sequence. Practice it 3 times before the hackathon.

### Pre-demo setup (10 minutes before):
```powershell
# In the module3-watermarking folder:
uvicorn app:app --port 8001 --reload
# Open http://localhost:8001 in the browser
# Verify demo_videos/ has the normalized source videos from Module 1
# Verify the session registry starts empty
```

### On stage (~2.5 minutes):

**Part 1: Create 3 viewer copies (45 seconds)**

Embed panel:
- Pick `normalized_source_01.mp4` from `demo_videos/`
- Viewer Name: "Viewer A — BBC UK", Region: UK, Platform: Mobile App → Embed
- (While it processes, explain what's happening: "Embedding unique invisible IDs into pixel data, audio, and DCT coefficients...")
- When done: download link appears

Repeat twice more:
- "Viewer B — ESPN US", Region: US, Platform: Smart TV → Embed
- "Viewer C — Star Sports India", Region: India, Platform: Web Browser → Embed

"Three different viewers, three uniquely watermarked copies of the same video."

**Part 2: Simulate piracy (20 seconds)**

```powershell
# Run in a second terminal, already open:
python attack_generator.py watermarked_outputs\viewerb_espn_us_normalized_source_01.mp4
```

"Let's say Viewer B leaked the stream. A pirate grabbed it, mirrored it, stripped the audio, and reuploaded it."

**Part 3: Attribute the leak (60 seconds)**

Extract panel — upload 3 attacked clips one by one:

1. `...viewerb..._01_mirrored.mp4` → ATTRIBUTED: Viewer B. "Mirrored — Layer 1 and 3 still caught it."
2. `...viewerb..._05_muted.mp4` → ATTRIBUTED: Viewer B. "Audio stripped — Layer 2 shows 0% but 1 and 3 agree."
3. `...viewerb..._02_cropped.mp4` → ATTRIBUTED: Viewer B. "Cropped 30% — Layer 3's DCT method was built for exactly this."

"Every attack. Same answer. Viewer B. ESPN US. Smart TV. Session ID a1b2c3d4."

Bonus if time: upload a clip from Viewer A's copy — correctly attributes to Viewer A, not Viewer B. "No false attribution."

**Part 4: Connect to Module 1 (15 seconds)**

"Module 1 told us this content was ours. Module 3 tells us who leaked it. Same attacked clip, two different questions, two definitive answers."

---

## 9. Testing Checklist (Before Demo)

Run every item below. Fix anything that fails before going on stage.

- [ ] Server starts on port 8001 without errors
- [ ] Page loads at http://localhost:8001
- [ ] Embed Viewer A, B, C — all three produce downloadable files
- [ ] Session registry shows all 3 entries after embedding
- [ ] Run `attack_generator.py` on Viewer B's watermarked copy — 8 attacked clips produced
- [ ] Extract from original watermarked copy → ATTRIBUTED to Viewer B, confidence >80%
- [ ] Extract from mirrored attack → ATTRIBUTED to Viewer B
- [ ] Extract from recolored attack → ATTRIBUTED to Viewer B
- [ ] Extract from re-encoded (low quality) attack → ATTRIBUTED to Viewer B
- [ ] Extract from muted attack → ATTRIBUTED to Viewer B (L1+L3 only, L2=0%)
- [ ] Extract from cropped attack → ATTRIBUTED to Viewer B (L3 saves it)
- [ ] Extract from sped-up attack → ATTRIBUTED (or PARTIAL — document this)
- [ ] Extract from logo-overlay attack → ATTRIBUTED to Viewer B
- [ ] Extract from 15-second trimmed clip → PARTIAL or ATTRIBUTED (short clips are harder)
- [ ] Extract from Viewer A's copy → correctly attributes to Viewer A (not Viewer B)
- [ ] Extract from an unrelated video (negative control) → NOT ATTRIBUTED
- [ ] `/api/reset` clears registry and deletes watermarked outputs
- [ ] Embed a video: temp files are cleaned up after (no leftover PNG files in temp_processing)
- [ ] Processing time for a 90-second video: under 90 seconds (aim for <60s)
- [ ] UI spinner shows during long operations (doesn't look frozen)
- [ ] Download link works — file downloads correctly

---

## 10. Critical Implementation Rules for Claude Code

1. **PNG frames only.** Use PNG (not JPG) for frame extraction during processing. JPG compression modifies pixel values and will corrupt the spread-spectrum signal before you even embed it. Only convert to a compressed format during video reassembly via FFmpeg.

2. **Same key = same positions.** The HMAC-based position generation must return identical results for embed and extract given the same frame number and secret key. Test this explicitly: `get_block_positions(0, 144, 720, 1280, 32)` called twice must return the identical list.

3. **Reed-Solomon is your safety net, not a miracle.** RS can recover from ~15-27% bit corruption. If more than ~30% of bits are wrong (very heavy re-encoding), RS will fail and return None. This is expected behavior — document it, don't try to fix it. The 2-of-3 layer rule compensates for individual layer failures.

4. **Always clean up temp files.** Every function that creates temp directories must use `try/finally` to ensure cleanup. A failed embed that leaves 500 PNG files in `temp_processing/` will crash the disk before demo day.

5. **Never block the FastAPI event loop.** Embedding 3 watermark layers in a 90-second video can take 30-90 seconds. Use `asyncio.to_thread(embed_full, ...)` inside the endpoint. Without this, the browser will appear frozen and the UI spinner will never update.

6. **Graceful degradation per layer.** If Layer 2 extraction fails (e.g., muted video), it must return `{"confidence": 0, "session_id_int": None}` — not an exception. The extractor should handle this and continue with Layers 1 and 3. Two layers agreeing is still a valid attribution.

7. **Audio is optional.** Some of the Module 1 demo videos may not have audio, or the audio is very quiet. Always check `has_audio` before attempting Layer 2 extraction. Return a clear status like `"no_audio"` so the UI can show "Layer 2: skipped — no audio track" instead of "failed."

8. **Test on the actual attacked clips from Module 1.** Don't invent test cases. Run the exact same `attack_generator.py` attacks on watermarked videos and verify extraction works. The demo uses these exact files.

9. **Threshold tuning is expected.** The config values in Section 4 are reasonable starting points. You will almost certainly need to adjust `L1_NOISE_STRENGTH`, `L1_CORRELATION_THRESHOLD`, `L3_QUANTIZATION_STEP`, and `FUSION_OVERALL_THRESHOLD` after testing on real videos. Tune by running extraction on attacked clips and checking confidence scores. If confidence is too low across the board, increase noise/quantization strength.

10. **Short videos are harder.** A 15-second trimmed clip has fewer frames and fewer audio repetitions to average over. Layer 4's DNA approach (from Module 1) doesn't apply here — shorter clips just have lower confidence. Document this: "Clips shorter than 15 seconds may return PARTIAL attribution."

11. **Don't try to watermark in real-time.** This is offline forensic watermarking — the video is processed as a file. Real-time stream watermarking (per-viewer CDN edge injection) is a production concern, not a demo concern. Mention it in the architecture slide.

---

## 11. What NOT to Build

Skip these explicitly. They go in the "production roadmap" slide.

- **Real-time streaming watermarking** — we process files, not live streams
- **CDN cache-control enforcement** — mention it verbally, not in code
- **Database (PostgreSQL)** — JSON file is fine for demo
- **User authentication** — zero auth
- **Multiple secret key management** — one hardcoded key for demo
- **Perceptual robustness evaluation tools** — tune manually
- **Watermark strength/visibility tradeoff UI** — single fixed config
- **Docker** — run directly on Windows
- **Tests** — manual testing against checklist above

---

## 12. How Module 3 Connects to Modules 1 and 2

Do NOT build this integration. Just say it verbally during the demo.

**Module 1 + Module 3:**
- Module 1 says: "This clip on X (Twitter) is our content — 94% confidence"
- Module 3 says: "And session ID a1b2c3d4 leaked it — Viewer B, ESPN US, Smart TV, 20:47 UTC"
- Same clip. Same attacked version. Two different answers from two different systems.

**Module 2 + Module 3:**
- Module 2 finds the pirated clip on Telegram/Twitter via Apify scraping
- The domain or URL is logged in the threat graph
- Module 3 analyzes the clip that Module 2 found and identifies the source session
- "Our crawler found this clip on @streamking2024's Twitter. Our watermark engine says it came from session ID a1b2c3d4 — a Smart TV account in the United States registered 4 hours before the match."

**The pitch line:**
"Three modules. One system. We find the content, we map the network, we identify the leaker. That's end-to-end digital asset protection."

---

## 13. Final Notes for Claude Code

Build in the order specified in Section 5. Do not skip checkpoints. The system only works end-to-end once all three layers and the fusion are complete, but each layer can be tested independently at its checkpoint.

The single most important thing to get right is **the HMAC key derivation in `common.py`**. If `get_block_positions(frame_number=0, ...)` returns different results on embed vs extract, nothing will work and the bug will be extremely hard to find. Test this in a REPL as the very first thing after writing `common.py`.

The second most important thing is **PNG for frames**. If you accidentally use JPG during the intermediate frame processing stages, Layer 1 will silently fail — the spread spectrum signal will be destroyed by JPEG compression and correlations will be near zero. The bug looks like "Layer 1 never detects anything" and takes an hour to diagnose. Use PNG. Always.

The third most important thing is **Reed-Solomon**. Without RS, a single bit error in the session ID produces a completely wrong ID. With RS, up to ~27% of bits can be wrong and the correct ID is still recovered. RS is what makes the system work in practice rather than just in a pristine test environment.

Test on real attacked videos from Module 1's `attack_generator.py`. Don't rely on synthetic tests.

Good luck. The math is solid. The implementation is straightforward. Build carefully and it will work.
