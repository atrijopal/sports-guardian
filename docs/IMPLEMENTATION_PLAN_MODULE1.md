# Module 1 — Advanced Multi-Layer Video Fingerprinting
## Hackathon Demo Implementation Plan (for Claude Code)

---

## 0. Read This First (Context for Claude Code)

You are building a **video fingerprinting system** that identifies whether a suspect video clip came from a protected source video, even when the suspect clip has been heavily modified (mirrored, cropped, recolored, sped up, muted, trimmed, logo-stamped, re-encoded).

This is **Module 1** of a larger "Digital Asset Protection" system for sports media. Modules 2+ (watermarking, web scraping, takedown automation) are out of scope. Build only Module 1.

**This is a hackathon demo**, not production. Optimize for:
1. **Visible impressiveness on stage** — the demo must survive live attacks by judges
2. **Reliability under time pressure** — no mystery bugs, no flaky dependencies
3. **Simple storage** — JSON file, not Postgres. Brute-force Python lists, not FAISS. These are in the architecture slide but NOT in the demo code.
4. **Windows compatibility** — target machine is Windows with FFmpeg and fpcalc in PATH
5. **~10 hour build budget**

**The target experience:**
- User opens a web page in their browser
- User clicks "Register Video", picks an official match video → system fingerprints it, shows success
- User clicks "Check Suspect Clip", picks a (possibly modified) clip → system returns: match/no-match, which original it matched, confidence score, and a per-layer breakdown
- System catches mirrored, cropped, recolored, sped-up, muted, trimmed, logo-overlaid clips
- System correctly rejects unrelated videos (negative controls)

---

## 1. What the System Does (Broader View)

### The Problem
Sports broadcasters lose massive value when official matches get ripped, modified, and reuploaded across social media and illegal streaming sites. Simple hash-based detection (MD5, SHA-256) fails because any pixel change breaks the hash. Pirates routinely mirror, crop, recolor, speed-shift, and re-encode clips specifically to defeat detection.

### The Solution
A **multi-layer fingerprinting system** that identifies videos by their *visual*, *audio*, and *structural-temporal* characteristics. Each layer captures a different aspect of the video, and together they survive attacks that any single layer would miss.

### The Four Layers

**Layer 1 — Visual pHash (Perceptual Hashing)**
Extracts frames from the video, normalizes them (strips letterboxing, canonicalizes mirroring, masks logo regions, equalizes brightness), and computes perceptual hashes that are robust to compression, resizing, color shifts, and minor visual edits.

**Layer 2 — Audio Chromaprint**
Extracts the audio track, generates acoustic fingerprints via Chromaprint (the same tech behind Shazam-like systems), and uses sliding-window matching to find where a suspect clip appears in an original, even if timestamps are offset.

**Layer 4 — Match DNA (Event Sequence Fingerprinting)** ← headline differentiator
Captures the *temporal rhythm* of the match as a sequence of visual/audio/motion energy peaks, encodes it as a short string, and uses fuzzy substring matching to identify which match a clip came from. Survives speed changes, recoloring, dubbing, and most heavy attacks because it measures macro-level broadcast structure, not pixels.

**Fusion Layer**
Combines per-layer similarity scores into a single confidence score with a threshold decision, and shows per-layer breakdown in the UI so judges can see *which* layers caught each attack.

**Note:** Layer 3 (motion) from the original plan is intentionally skipped for the demo. It adds complexity without adding a visible win on stage. Mention it exists in the architecture but don't build it.

### Why This Wins
- Pre-normalization pipeline kills mirroring, cropping, recoloring, logo overlays *at the input stage*
- Layer 4 (DNA) is the thing no other team will have, and it demos beautifully on sped-up and recolored clips
- Per-layer breakdown in the UI makes the system feel transparent and trustworthy to judges
- Everything is free, local, and offline — no API keys, no cloud, no GPU

---

## 2. Tech Stack (All Free, All Offline)

**Language:** Python 3.10+

**External binaries (must be installed on Windows PATH):**
- `ffmpeg` — frame and audio extraction (https://www.gyan.dev/ffmpeg/builds/)
- `fpcalc` — Chromaprint audio fingerprinting (https://acoustid.org/chromaprint)

**Python packages (pip-installable):**
- `fastapi` — web backend
- `uvicorn[standard]` — ASGI server
- `python-multipart` — file upload support for FastAPI
- `opencv-python` — frame processing, normalization
- `Pillow` — image resizing
- `imagehash` — pHash, dHash, wHash
- `numpy` — numerical work
- `scipy` — peak detection for Layer 4
- `librosa` — audio energy extraction for Layer 4
- `soundfile` — librosa dependency
- `rapidfuzz` — fuzzy substring matching for Layer 4 DNA
- `pyacoustid` — Python wrapper for fpcalc (Layer 2)

**Storage:** Single JSON file (`fingerprints_db.json`). No SQL, no FAISS. Brute-force search over a Python list. This is fine for a demo with <20 videos.

**Frontend:** Single static HTML file with vanilla JS. No React, no build step.

---

## 3. Project Structure

Create exactly this structure:

```
sports-fingerprint-demo/
├── requirements.txt
├── README.md
├── app.py                      # FastAPI server, routes, orchestration
├── storage.py                  # JSON-file "database" with list of fingerprints
├── attack_generator.py         # FFmpeg-based attack script (already written)
├── config.py                   # All tunable thresholds in one place
├── fingerprint/
│   ├── __init__.py
│   ├── normalize.py            # Pre-normalization pipeline
│   ├── layer1_visual.py        # pHash with normalization
│   ├── layer2_audio.py         # Chromaprint + sliding window
│   ├── layer4_dna.py           # Event-peak DNA + rapidfuzz
│   └── fusion.py               # Combine scores + decision
├── static/
│   └── index.html              # Single-page UI
├── demo_videos/                # User places source videos here
│   └── attacks/                # Generated by attack_generator.py
└── fingerprints_db.json        # Created at runtime
```

---

## 4. Config File (`config.py`)

Put all thresholds in one place so they can be tuned without hunting through modules:

```python
# config.py
# All tunable parameters in one place. Tune during testing, not during demo.

# ---- Layer 1: Visual pHash ----
L1_FRAME_SAMPLE_INTERVAL_SEC = 2.0        # Extract one frame every N seconds
L1_HASH_SIZE = 8                          # 8x8 = 64-bit hash
L1_HAMMING_MATCH_THRESHOLD = 12           # Max Hamming distance to count as frame match
L1_MIN_MATCHED_FRAMES_RATIO = 0.3         # Fraction of suspect frames that must match

# ---- Layer 2: Audio Chromaprint ----
L2_SAMPLE_RATE = 44100
L2_XOR_BIT_THRESHOLD = 10                 # Max avg differing bits per 32-bit int
L2_MIN_OVERLAP_SEC = 3.0                  # Minimum overlap for a valid match

# ---- Layer 4: Match DNA ----
L4_ENERGY_SAMPLE_HZ = 1.0                 # One energy sample per second
L4_PEAK_PROMINENCE_VISUAL = 0.15          # scipy find_peaks prominence (normalized 0-1)
L4_PEAK_PROMINENCE_AUDIO = 0.15
L4_PEAK_PROMINENCE_MOTION = 0.15
L4_MIN_DNA_LENGTH = 3                     # Suspect clip must have >= N events
L4_FUZZY_MATCH_THRESHOLD = 70             # rapidfuzz partial_ratio 0-100

# ---- Fusion ----
FUSION_WEIGHTS = {"layer1": 0.45, "layer2": 0.35, "layer4": 0.20}
FUSION_MATCH_THRESHOLD = 0.55             # Overall score to flag as match
FUSION_MIN_AGREEING_LAYERS = 2            # At least N layers must individually agree

# ---- Normalization ----
NORM_TARGET_SIZE = (256, 256)             # Resize after cropping
NORM_LOGO_MASK_RATIO = 0.15               # Top-left + bottom-right mask size
NORM_LETTERBOX_THRESHOLD = 15             # Pixel variance below this = black bar

# ---- Paths ----
DB_PATH = "fingerprints_db.json"
DEMO_VIDEOS_DIR = "demo_videos"
TEMP_DIR = "temp_processing"
```

---

## 5. Module-by-Module Build Order

**Build in this exact order.** Each step has a working fallback, so at any checkpoint you have a demoable system.

### Checkpoint 1: Bare skeleton (30 min)
1. Create folder structure
2. Write `requirements.txt`
3. Write `config.py`
4. Write `storage.py` with load/save/list functions
5. Write minimal `app.py` with `/` → static HTML, `/api/register`, `/api/check` stub endpoints
6. Write minimal `static/index.html` with two file-upload buttons
7. **Verify:** `uvicorn app:app --reload` works, page loads, uploads reach backend (even if they do nothing)

### Checkpoint 2: Layer 1 end-to-end (2 hours)
1. Write `fingerprint/normalize.py` — pre-normalization pipeline
2. Write `fingerprint/layer1_visual.py` — frame extraction, hashing, matching
3. Wire Layer 1 into `/api/register` and `/api/check`
4. **Verify:** register a source video, check it against itself → match with ~100% score. Check it against a mirrored version → still matches.

### Checkpoint 3: Layer 2 end-to-end (2 hours)
1. Write `fingerprint/layer2_audio.py` — audio extraction, Chromaprint, sliding window match
2. Wire Layer 2 into the pipeline
3. **Verify:** muted clips fail Layer 2 (expected), audio-preserving attacks pass Layer 2

### Checkpoint 4: Layer 4 DNA end-to-end (3 hours — hardest)
1. Write `fingerprint/layer4_dna.py` — energy extraction, peak detection, DNA string encoding, rapidfuzz matching
2. Wire Layer 4 into the pipeline
3. **Verify:** sped-up clips (where Layers 1 and 2 weaken) still match via Layer 4

### Checkpoint 5: Fusion and polish (1.5 hours)
1. Write `fingerprint/fusion.py` — weighted combine, threshold, per-layer breakdown
2. Polish the HTML: show per-layer scores, colors, match result card
3. Run all attack types end-to-end, tune thresholds in `config.py` if needed

### Checkpoint 6: Final testing (1 hour)
1. Run full attack sweep on 3–5 source videos
2. Run negative controls (unrelated videos should NOT match)
3. Prepare demo script: which clips to show, in what order

---

## 6. Detailed Specs — Module by Module

### 6.1 `storage.py`

Simple JSON-backed list of fingerprints. Each entry:

```python
{
  "video_id": "uuid4-string",
  "name": "normalized_source_01.mp4",
  "registered_at": "ISO-8601-timestamp",
  "duration_sec": 90.5,
  "layer1": {
    "frame_hashes": [{"timestamp": 0.0, "hash_hex": "abc123..."}, ...]
  },
  "layer2": {
    "chromaprint_ints": [123456, 789012, ...],
    "duration": 90.5
  },
  "layer4": {
    "dna_string": "A7C4M3A2C9...",
    "events": [{"t": 3.2, "type": "A"}, ...]
  }
}
```

**Functions to implement:**
- `load_db() -> list[dict]` — read JSON file, return `[]` if missing
- `save_db(db: list[dict]) -> None` — write JSON file with indent=2
- `add_fingerprint(entry: dict) -> None` — append and save
- `list_fingerprints() -> list[dict]` — return metadata only (no hashes, for UI)
- `get_all_fingerprints() -> list[dict]` — full entries for matching

Keep it dumb. No locking, no migrations, no schema validation.

### 6.2 `fingerprint/normalize.py`

**Purpose:** Given a raw video frame (BGR numpy array from OpenCV), produce a canonical grayscale frame that is robust to common pirate attacks.

**Functions:**

```python
def strip_letterbox(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Detect top/bottom/left/right black bars by row/column variance
    below config.NORM_LETTERBOX_THRESHOLD and crop them out.
    Returns cropped BGR frame.
    """

def center_crop_square(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Take the central square region (80% of the shorter side).
    Makes mild cropping attacks a no-op.
    """

def mask_logo_regions(gray: np.ndarray) -> np.ndarray:
    """
    Zero out top-left and bottom-right 15% squares.
    Returns grayscale with those regions blacked out.
    """

def histogram_equalize(gray: np.ndarray) -> np.ndarray:
    """
    cv2.equalizeHist to kill brightness/contrast/gamma attacks.
    """

def canonicalize_frame(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Full pipeline:
      strip_letterbox → center_crop_square → grayscale → resize to
      NORM_TARGET_SIZE → mask_logo_regions → histogram_equalize
    Returns a normalized 2D numpy grayscale array ready for hashing.
    """
```

**Note on mirror canonicalization:** This is handled in `layer1_visual.py`, not here. For each frame, we compute the hash of both the normalized frame AND its horizontal flip, then store/compare the lexicographically smaller one. This makes mirroring a no-op.

### 6.3 `fingerprint/layer1_visual.py`

**Purpose:** Extract frames via FFmpeg, normalize them, compute perceptual hashes, and match.

**Functions:**

```python
def extract_frames(video_path: str, out_dir: str,
                   interval_sec: float) -> list[tuple[float, str]]:
    """
    Run ffmpeg to extract one frame every interval_sec seconds.
    Save as JPGs in out_dir/frame_%06d.jpg.
    Return list of (timestamp_sec, filepath) tuples.

    FFmpeg command:
      ffmpeg -i <video> -vf fps=1/<interval> -q:v 3 <out_dir>/frame_%06d.jpg

    Use subprocess.run, capture stderr, raise RuntimeError on nonzero exit.
    """

def hash_frame(frame_path: str) -> str:
    """
    Load JPG with cv2.imread, pass through canonicalize_frame from normalize.py,
    convert to PIL Image, compute imagehash.phash with hash_size=8.
    Also compute phash of horizontally-flipped version.
    Return the lexicographically smaller hex string (mirror canonicalization).
    """

def generate_fingerprint(video_path: str) -> dict:
    """
    Full pipeline: extract frames → hash each → return dict:
      {"frame_hashes": [{"timestamp": 0.0, "hash_hex": "..."}, ...]}
    Clean up temp frames after.
    """

def hamming_distance(hex1: str, hex2: str) -> int:
    """XOR two hex strings interpreted as ints, return popcount."""

def match_fingerprints(suspect: dict, original: dict) -> float:
    """
    For each suspect frame hash, find the minimum Hamming distance to any
    original frame hash. Count it as "matched" if distance <=
    L1_HAMMING_MATCH_THRESHOLD.

    Return score = matched_count / total_suspect_frames (0.0 to 1.0).

    If fewer than L1_MIN_MATCHED_FRAMES_RATIO of suspect frames match,
    return 0.0 (hard fail, prevents noise).
    """
```

**Temp file handling:** Use `tempfile.mkdtemp()` for frame extraction, `shutil.rmtree()` in a `finally` block. Never leave junk in the project folder.

### 6.4 `fingerprint/layer2_audio.py`

**Purpose:** Extract audio, compute Chromaprint fingerprint, match via sliding window.

**Functions:**

```python
def extract_audio_wav(video_path: str, out_path: str) -> None:
    """
    Run ffmpeg to extract audio as 44.1kHz mono WAV.
      ffmpeg -i <video> -vn -acodec pcm_s16le -ar 44100 -ac 1 <out>
    If video has no audio track, create an empty wav (1 second silence)
    so downstream code doesn't crash. Log a warning.
    """

def compute_chromaprint(wav_path: str) -> tuple[list[int], float]:
    """
    Use pyacoustid.fingerprint_file or call fpcalc directly via subprocess.
    Returns (list_of_32bit_ints, duration_sec).

    Prefer subprocess call to fpcalc -raw <wav> for reliability:
      parse stdout for DURATION= and FINGERPRINT= lines.
      The fingerprint line is comma-separated ints after decoding.
    """

def generate_fingerprint(video_path: str) -> dict:
    """
    Full pipeline: extract wav → chromaprint → return
      {"chromaprint_ints": [...], "duration": 90.5}
    """

def xor_distance(a: int, b: int) -> int:
    """Popcount of (a XOR b) masked to 32 bits."""

def sliding_window_match(suspect_ints: list[int],
                         original_ints: list[int]) -> float:
    """
    Slide the shorter fingerprint across the longer one. At each offset,
    compute average XOR bit distance across the overlapping region.

    Return score = 1.0 - (best_avg_bits / 32.0), clamped to [0, 1].

    If the best match has avg bits > L2_XOR_BIT_THRESHOLD, return 0.0.
    If suspect is empty or too short, return 0.0.
    """

def match_fingerprints(suspect: dict, original: dict) -> float:
    """Wrapper: unpack dicts and call sliding_window_match."""
```

**Critical:** Handle the "no audio" case gracefully. Muted clips should return Layer 2 score of 0.0 without crashing. Layers 1 and 4 will pick up the slack.

### 6.5 `fingerprint/layer4_dna.py`

**Purpose:** Extract visual/audio/motion energy signals, find peaks, encode as a DNA string, match with fuzzy substring search.

**Functions:**

```python
def extract_energy_signals(video_path: str) -> dict:
    """
    Produce three 1-Hz time series over the video duration:

    1. visual_energy: for each second, mean abs diff between this second's
       frame and the previous second's frame. Use ffmpeg to extract 1fps
       frames to temp dir, then cv2.absdiff on consecutive grayscale frames.

    2. audio_energy: librosa.load the audio, compute RMS with frame_length
       matched to 1-second hops. Normalize to [0,1].

    3. motion_energy: same as visual_energy for now (we're not building
       Layer 3, so reuse this signal under a different peak-detection tune).
       OR: for simplicity, just use visual_energy and skip motion as a
       separate channel. Trade-off: fewer events but simpler code.

    Return {"visual": [...], "audio": [...], "duration": N}
    Both arrays are length = int(duration).
    """

def detect_peaks(signal: list[float], prominence: float) -> list[int]:
    """
    Use scipy.signal.find_peaks with the given prominence.
    Normalize signal to [0,1] first.
    Return list of peak indices (seconds).
    """

def build_dna_string(energy: dict) -> tuple[str, list[dict]]:
    """
    Run peak detection on visual and audio signals.
    Merge peaks into a single timeline, sorted by timestamp.
    Encode each peak as a character: 'V' = visual, 'A' = audio.
    Between consecutive events, insert a gap character based on QUANTIZED
    GAP RATIO, not absolute gap (for speed invariance).

    Encoding scheme:
      - For each consecutive pair of events, compute gap in seconds
      - Quantize to: 's' (short, <3s), 'm' (medium, 3-8s), 'l' (long, >8s)
      - String looks like: "V s A m V l A s V ..."
      - Store without spaces: "VsAmVlAsV"

    Return (dna_string, events_list) where events_list is
    [{"t": 3.2, "type": "V"}, ...] for debugging/display.
    """

def generate_fingerprint(video_path: str) -> dict:
    """
    Full pipeline: extract energies → build DNA → return
      {"dna_string": "...", "events": [...]}
    """

def match_fingerprints(suspect: dict, original: dict) -> float:
    """
    Use rapidfuzz.fuzz.partial_ratio to find the best substring match
    of suspect["dna_string"] within original["dna_string"].

    If suspect DNA length < L4_MIN_DNA_LENGTH * 2 (accounting for gap
    chars), return 0.0 (not enough events to be confident).

    Return score = partial_ratio / 100.0 (0.0 to 1.0).
    If score < L4_FUZZY_MATCH_THRESHOLD/100, return 0.0 (hard fail).
    """
```

**Critical notes for Layer 4:**
- **Peak prominence is the #1 thing to tune.** Too low → noise events, too high → no events. Start at 0.15 on [0,1]-normalized signals. During testing, print the event count per video; aim for ~1 event per 3–5 seconds of video.
- **Short videos are a problem.** A 30-second video might only produce 5–8 events. Document in the README that Layer 4 is most reliable on clips ≥45 seconds.
- **Speed invariance comes from the ratio encoding**, not from the absolute gaps. If you encode gaps in absolute seconds, a 1.25× speed attack breaks Layer 4. Quantized-gap-bucket encoding preserves the *relative* rhythm.

### 6.6 `fingerprint/fusion.py`

**Purpose:** Combine layer scores into a final decision and a human-readable result.

```python
def fuse(layer1_score: float, layer2_score: float,
         layer4_score: float) -> dict:
    """
    Weighted average using FUSION_WEIGHTS.
    Count how many layers individually cleared their own threshold:
      - Layer 1 agrees if score >= 0.35
      - Layer 2 agrees if score >= 0.50
      - Layer 4 agrees if score >= 0.60
    (These are separate from the overall threshold.)

    Return dict:
    {
      "overall_score": 0.78,
      "is_match": True,
      "agreeing_layers": 2,
      "per_layer": {"layer1": 0.85, "layer2": 0.0, "layer4": 0.72},
      "verdict": "MATCH" | "NO_MATCH" | "WEAK_MATCH",
      "explanation": "Matched on visual + DNA. Audio was stripped."
    }

    is_match = True iff:
      overall_score >= FUSION_MATCH_THRESHOLD
      AND agreeing_layers >= FUSION_MIN_AGREEING_LAYERS

    Build explanation string by listing which layers agreed and
    naming any that failed with plausible reasons.
    """

def best_match(suspect_fp: dict, all_originals: list[dict]) -> dict:
    """
    Run suspect against every registered original via all three layers.
    Pick the one with the highest overall fused score.
    Return full result dict including matched original's metadata,
    OR {"is_match": False, ...} if nothing clears the threshold.
    """
```

### 6.7 `app.py` — FastAPI Server

**Endpoints:**

```python
GET  /                      → serve static/index.html
GET  /api/list              → return list of registered videos (metadata only)
POST /api/register          → multipart file upload, run all 3 layers, save to DB
POST /api/check             → multipart file upload, match against all, return best
POST /api/reset             → wipe the database (handy for demos)
```

**Implementation details:**
- Use `UploadFile` from FastAPI for file uploads
- Save uploads to a temp path, process, then delete
- Return JSON responses; let the HTML render them
- CORS: allow all origins (`CORSMiddleware` with `allow_origins=["*"]`) so the UI can call the API even if loaded from file://
- Wrap each endpoint in try/except and return `{"error": str(e)}` with HTTP 500 on failure — don't let the server crash mid-demo
- Log every step with timestamps so you can see what's slow

**Registration flow:**
```
1. Save upload to temp file
2. Call layer1_visual.generate_fingerprint(temp_path)
3. Call layer2_audio.generate_fingerprint(temp_path)
4. Call layer4_dna.generate_fingerprint(temp_path)
5. Assemble entry dict with uuid, name, timestamp, all three fingerprints
6. storage.add_fingerprint(entry)
7. Delete temp file
8. Return {"status": "ok", "video_id": ..., "name": ..., "duration": ...}
```

**Check flow:**
```
1. Save upload to temp file
2. Generate all three fingerprints for the suspect
3. Load all originals from DB
4. Call fusion.best_match(suspect_fp, all_originals)
5. Delete temp file
6. Return the full match result dict
```

### 6.8 `static/index.html`

Single page with two cards side by side:

**Left card: "Register Official Video"**
- File input (accept="video/*")
- "Register" button
- Status area that shows progress and success/failure
- Below: list of currently registered videos, fetched from `/api/list` on load and after each register

**Right card: "Check Suspect Clip"**
- File input
- "Check" button
- Result area that shows:
  - Big verdict banner: green "MATCH FOUND" / red "NO MATCH" / yellow "WEAK MATCH"
  - Matched video name and registration date
  - Overall confidence score (large, percentage)
  - Per-layer breakdown as a horizontal bar chart:
    - Layer 1 (Visual): ████████░░ 82%
    - Layer 2 (Audio): ██████████ 95%
    - Layer 4 (DNA): ███████░░░ 71%
  - Explanation text ("Matched on visual + audio. DNA match weak due to short clip.")

**Visual style:**
- Dark theme (easier to photograph on stage)
- Monospace font for numbers
- Subtle animations on score bars
- No external CSS frameworks — vanilla CSS, <200 lines

**JS behavior:**
- Vanilla fetch() calls to `/api/*`
- Show a spinner during processing (fingerprinting takes 5–15 seconds)
- Disable buttons while a request is in flight
- On page load, fetch `/api/list` and populate registered videos section

Keep it simple. One HTML file. No framework. No bundler. You can literally open it in Notepad to tweak on stage if needed.

---

## 7. Attack Generator

The `attack_generator.py` script is already written and provided separately. It takes a source video and produces 8 attacked versions using FFmpeg:
1. Horizontal mirror
2. Center crop 70%
3. Hue rotation + saturation
4. 1.25× speed-up (video + audio)
5. Muted (no audio)
6. Trimmed to first 15 seconds
7. Low-bitrate re-encode
8. "PIRATE TV" text overlay

Drop that file into the project root as-is.

---

## 8. requirements.txt

```
fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9
opencv-python>=4.9
Pillow>=10.0
imagehash>=4.3
numpy>=1.26
scipy>=1.12
librosa>=0.10
soundfile>=0.12
rapidfuzz>=3.6
pyacoustid>=1.3
```

---

## 9. README.md Content

Include a README that covers:

1. **What this is** — one paragraph summary
2. **Prerequisites** — Python 3.10+, FFmpeg, fpcalc, with Windows install links
3. **Setup** — `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`
4. **How to run** — `uvicorn app:app --reload`, then browse to `http://localhost:8000`
5. **How to prepare demo videos** — normalize command, attack generator usage
6. **Demo script** — suggested order of actions for a live demo
7. **Known limitations** — Layer 4 needs ≥45s clips, muted clips lose Layer 2, etc.
8. **Troubleshooting** — "ffmpeg not found" → add to PATH, "fpcalc not found" → same

---

## 10. Critical Implementation Rules for Claude Code

These are non-negotiable to keep the demo reliable:

1. **Never leave temp files behind.** Every function that creates temp files wraps cleanup in `try/finally`.

2. **Never crash mid-request.** Every endpoint catches exceptions and returns a JSON error. A stack trace during a live demo is death.

3. **Always log with timestamps.** Use Python's `logging` module. Every major step prints `[HH:MM:SS] Layer 1 hashing...`. During demo you can see progress in the terminal.

4. **Never hardcode paths.** All paths come from `config.py`. Use `pathlib.Path`, not string concatenation.

5. **Never block the event loop hard.** Fingerprinting is CPU-bound and slow. Use `asyncio.to_thread()` or `run_in_executor` when calling fingerprint functions from FastAPI routes, otherwise the UI appears frozen during uploads.

6. **Never trust input video durations.** Use ffprobe or librosa to measure actual duration; don't parse filenames.

7. **Always make Layer 2 degrade gracefully when audio is missing.** Muted attack must not crash the pipeline.

8. **Always make Layer 4 degrade gracefully when video is too short.** Return 0.0, let Layers 1 and 2 handle it.

9. **Always use `shell=False`** in subprocess calls for FFmpeg/fpcalc. Windows path handling with `shell=True` is a landmine.

10. **Test on Windows paths with spaces.** Use `str(Path(x))` when passing paths to subprocess, and make sure every subprocess call accepts paths with spaces correctly.

---

## 11. Testing Checklist (Before Demo)

Run this before walking on stage:

- [ ] Register 3 source videos, verify all 3 appear in `/api/list`
- [ ] Check each source against itself → MATCH with >90% score
- [ ] Check mirrored version → MATCH (Layer 1 normalization working)
- [ ] Check cropped version → MATCH
- [ ] Check recolored version → MATCH
- [ ] Check 1.25× sped-up version → MATCH (Layer 4 DNA saving the day)
- [ ] Check muted version → MATCH (Layers 1+4, Layer 2 shows 0%)
- [ ] Check 15-second trimmed version → MATCH (lower confidence is fine)
- [ ] Check low-bitrate re-encode → MATCH
- [ ] Check logo-overlaid version → MATCH
- [ ] Check negative control (unrelated video) → NO MATCH
- [ ] Check negative control #2 → NO MATCH
- [ ] `/api/reset` works and clears DB
- [ ] Per-layer scores appear in UI and make intuitive sense
- [ ] No temp files left in working directory after any operation
- [ ] Processing time for 90-second video is under 20 seconds

If any attack type fails, tune the threshold in `config.py`. Do not hack individual layer files.

---

## 12. What NOT to Build

Explicitly skip these to stay within the time budget:

- Layer 3 (motion) — mentioned in architecture, not in code
- FAISS — brute-force Python list search is fine for <20 videos
- PostgreSQL — JSON file is fine
- Celery/Redis — synchronous processing with `asyncio.to_thread` is fine
- LightGBM learned fusion — fixed weights from config are fine
- dHash/wHash alongside pHash — just pHash is fine
- MFCC alongside Chromaprint — just Chromaprint is fine
- User accounts, auth, sessions — zero auth
- Docker — run directly on Windows
- Tests — manual testing against the checklist is fine
- Deployment — localhost only

Every item above is a thing you can brag about in the "future work" slide without having to build.

---

## 13. Suggested Demo Script (2 minutes)

1. (15s) "Sports broadcasters lose millions to pirated clips. Simple hashing fails because pirates mirror, crop, recolor. Here's our solution."
2. (20s) Register 3 source videos on stage. Watch them appear in the list.
3. (20s) "Let's try the obvious attack — mirrored." Upload mirrored clip → MATCH with ~85% score, Layer 1 and 4 green.
4. (20s) "Now recolored and logo-stamped." Upload → MATCH, show per-layer breakdown.
5. (20s) "Sped up by 25% — this breaks most pHash systems." Upload → Layer 1 drops, Layer 2 drops, **Layer 4 DNA saves it**. Point at the Layer 4 bar. This is the money moment.
6. (15s) "Muted clip, because uploaders strip audio." Upload → Layer 2 is zero, Layers 1 and 4 still agree, overall MATCH.
7. (10s) "Unrelated video as a sanity check." Upload negative → NO MATCH, zero false positives.
8. (20s) Closing: architecture slide, mention FAISS/Postgres/LightGBM/dHash as production next steps, thank judges.

---

## 14. Final Notes for Claude Code

Build in the order specified in section 5. After each checkpoint, **stop and verify it works end-to-end** before moving on. Do not build all layers first and then integrate — integrate continuously.

When in doubt, prefer **explicit, boring Python** over clever tricks. This code will be debugged at 2 AM in a noisy venue on a Windows laptop. Every clever line is a potential demo-killer.

Write docstrings on every function. Include one-line comments explaining *why* any nontrivial parameter exists. Future-you at 2 AM will thank present-you.

When you finish each module, manually run it once from a Python REPL against a real test video before integrating into the FastAPI app. Unit-test-as-you-go, informally.

Good luck. Build carefully, demo boldly.
