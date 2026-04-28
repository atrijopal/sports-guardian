# Sports Guardian

**Multi-layer sports media Digital Asset Protection platform.**  
Video fingerprinting · Real-time piracy intelligence · Invisible watermarking

Built for the Google Hackathon 2025.

---

## What It Does

Sports Guardian is a three-module system that protects live sports broadcast rights end-to-end:

| Module | Role | Port |
|---|---|---|
| **Signal Intercept** (M1) | Identifies whether a suspect clip was ripped from a protected broadcast, surviving mirroring, re-encoding, muting, speed changes, logo overlays, and cropping | 8000 |
| **War Room** (M2) | Real-time piracy intelligence dashboard — monitors SSL certificate transparency logs, clusters piracy operators, hunts YouTube channels, runs AI threat briefings | 8002 |
| **Source Attribution** (M3) | Embeds invisible per-viewer watermarks into video streams so leaked footage can be traced back to the exact subscriber | 8001 |
| **Guardian Hub** | Unified command dashboard — all three modules in one interface | 8080 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Guardian Hub :8080                │
│          Unified command dashboard (iframes)        │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌───▼────────┐
    │  M1 :8000   │ │  M2 :8002  │ │  M3 :8001  │
    │Fingerprint  │ │Threat Intel│ │Watermarking│
    └─────────────┘ └────────────┘ └────────────┘
```

---

## Module 1 — Signal Intercept (Video Fingerprinting)

Identifies pirated clips using a **three-layer pipeline** that is robust to:

- Mirror / horizontal flip
- Re-encoding at different bitrates
- Muting or audio replacement
- Speed changes (±20%)
- Letterbox cropping
- Logo overlays
- Brightness / contrast shifts

### Layer 1 — Visual pHash
Extracts frames via FFmpeg, runs each through a normalization pipeline (letterbox strip → center crop → grayscale → logo mask → histogram equalization), then computes a 64-bit perceptual hash (pHash). **Mirror canonicalization**: stores the lexicographically smaller of `hash(frame)` and `hash(flipped_frame)`, making horizontal mirroring a no-op.

### Layer 2 — Audio Chromaprint
Extracts 44.1 kHz mono audio via FFmpeg, runs through `fpcalc -raw` (Chromaprint), then uses **sliding-window XOR distance matching** to locate the suspect clip within the original's fingerprint. Gracefully returns 0.0 for muted clips.

### Layer 4 — Match DNA
Extracts 1-Hz visual energy (frame-diff) and audio RMS signals, detects peaks with `scipy.signal.find_peaks`, encodes peaks as a DNA string with quantized gaps (`s`/`m`/`l`). **Fuzzy substring match** via `rapidfuzz.fuzz.partial_ratio`. Speed invariance comes from ratio encoding, not absolute timestamps.

### Fusion
Weighted average of all three layer scores. A match requires both the overall score to clear a threshold AND a minimum number of individual layers to agree.

```
overall = 0.45 × L1 + 0.35 × L2 + 0.20 × L4
match   = overall ≥ 0.55 AND agreeing_layers ≥ 2
```

---

## Module 2 — War Room (Threat Intelligence)

Real-time piracy intelligence powered by Google APIs and local AI.

### Data Ingestion
- **CertStream**: Monitors the global SSL certificate transparency log stream in real time. Every new certificate is scored against keyword lists, cheap TLD lists, and brand similarity checks.
- **Apify scrapers**: Twitter, Reddit, and Telegram collectors harvest piracy promotion links.

### Three-Tier Domain Scoring
1. **Tier 1** (instant): Keyword scoring, TLD penalty, known brand fuzzy match — flags in milliseconds
2. **Tier 2** (NLP): AI model classifies whether the domain is a piracy site — runs on batches of flagged domains
3. **Real-time Safe Browsing**: Google Safe Browsing API v4 confirms confirmed malware/social engineering threats

### Threat Graph
Nodes (domains, YouTube channels, Telegram channels, Twitter accounts, Reddit accounts, invite links) are connected by edges (promotes, links_to, same_operator, posted). Stored in `GraphStore` — an in-memory dict with atomic JSON persistence.

### Analysis Pipeline
- **Threat scoring**: Weighted combination of connection count, recency decay (`e^(-hours/48)`), and node type weight
- **Operator clustering**: Union-Find algorithm linking domains by shared TLD + registration time window + brand similarity + shared channels + shared IP
- **Lifecycle stages**: `setup → promotion → active → dormant` based on promotion edge count and recency

### AI Intelligence
- **Threat briefing**: Structured JSON threat assessment (level, summary, top threats, cluster analysis, actions, sports at risk) generated every 30 minutes
- **Operator profiles**: Per-node natural language intelligence profiles on demand
- **YouTube hunt**: Automated search for piracy channels using configurable query sets
- **AI backend**: Uses AI API with local Ollama (`llama3.1:8b`) as a silent fallback when quota is exhausted

---

## Module 3 — Source Attribution (Watermarking)

Embeds a **64-bit session ID** invisibly into every watermarked copy of a video. The session ID is protected by Reed-Solomon error correction and can survive:

- Re-encoding (H.264/H.265)
- Moderate compression artifacts
- Screen recording

### Layer 1 — Spread Spectrum Visual
Adds a pseudo-random noise pattern to 32×32 pixel blocks in every 5th frame. Block positions are determined by an **HMAC-SHA256 keyed RNG** seeded per frame number — invisible to the eye but detectable by correlation.

### Layer 2 — BPSK Audio
Encodes watermark bits as **Binary Phase Shift Keying** at 19 kHz carrier frequency (near-ultrasonic), repeated every 10 seconds. Detection uses a bandpass filter (18–20.5 kHz) followed by coherent correlation against the reference carrier.

### Layer 3 — DCT Coefficient Modulation
Divides each frame into 8×8 DCT blocks, selects blocks pseudo-randomly via HMAC-seeded RNG, and forces the parity of a mid-frequency coefficient to encode each bit. Uses quantization step of 15 and 6 blocks per bit for redundancy.

### Reed-Solomon Error Correction
All three layers encode the same 64-bit session ID protected by 10 Reed-Solomon error correction symbols (using `reedsolo`). This allows up to 5 byte errors to be corrected per layer.

### Extraction & Attribution
Upload a suspect clip → all three layers attempt extraction → votes are fused → session ID resolved → matched against the session registry to identify the original viewer, account, region, platform, and IP.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Video processing | FFmpeg, fpcalc (Chromaprint) |
| Visual hashing | imagehash (pHash), OpenCV |
| Audio analysis | librosa, soundfile, scipy |
| Fuzzy matching | rapidfuzz |
| Error correction | reedsolo (Reed-Solomon) |
| Threat graph | Custom GraphStore (dict + JSON) |
| Operator clustering | Union-Find |
| Certificate monitoring | certstream-python |
| AI intelligence | AI API · Ollama llama3.1:8b (fallback) |
| Safe Browsing | Google Safe Browsing API v4 |
| YouTube intel | YouTube Data API v3 |
| Frontend | Vanilla JS, vis-network (graph), Chakra Petch + Azeret Mono |
| Real-time comms | WebSocket (FastAPI) |

---

## Quick Start

**Prerequisites**: Python 3.11+, FFmpeg, fpcalc in PATH

```bash
# Module 1 — Fingerprinting
cd module1-fingerprinting
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --port 8000 --reload

# Module 2 — Threat Intelligence
cd module2-threat-intel
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --port 8002 --reload

# Module 3 — Watermarking
cd module3-watermarking
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --port 8001 --reload

# Guardian Hub
cd hub
python -m http.server 8080
```

Then open **http://localhost:8080**

---

## Configuration

All tunable parameters live in each module's `config.py`. API keys:

```
module1-fingerprinting/config.py   → GEMINI_API_KEY, YOUTUBE_API_KEY
module2-threat-intel/config.py     → GEMINI_API_KEY, YOUTUBE_API_KEY, SAFE_BROWSING_API_KEY
module3-watermarking/config.py     → WATERMARK_SECRET_KEY, WATERMARK_SALT
```

For AI features without API quota: install [Ollama](https://ollama.ai) and pull `llama3.1:8b`. Module 2 falls back automatically.

---

## Project Structure

```
sports-guardian/
├── module1-fingerprinting/
│   ├── app.py                  # FastAPI routes
│   ├── config.py               # All thresholds
│   ├── storage.py              # JSON fingerprint DB
│   ├── attack_generator.py     # FFmpeg attack scripts
│   └── fingerprint/
│       ├── normalize.py        # Frame canonicalization
│       ├── layer1_visual.py    # pHash + mirror canonicalization
│       ├── layer2_audio.py     # Chromaprint + sliding window
│       ├── layer4_dna.py       # Event-peak DNA + fuzzy match
│       └── fusion.py           # Score combiner + verdict
├── module2-threat-intel/
│   ├── app.py                  # FastAPI + WebSocket + background tasks
│   ├── config.py               # Scoring weights, API keys, intervals
│   ├── graph_store.py          # Threat graph (nodes + edges)
│   ├── scoring.py              # Threat scores, clustering, lifecycle
│   ├── google_services.py      # Safe Browsing, YouTube, AI services
│   ├── collectors/
│   │   ├── certstream_monitor.py
│   │   ├── apify_twitter.py
│   │   ├── apify_reddit.py
│   │   └── apify_telegram.py
│   ├── nlp/domain_classifier.py
│   └── parsers/link_extractor.py
├── module3-watermarking/
│   ├── app.py                  # FastAPI routes
│   ├── config.py               # Watermark parameters
│   ├── session_registry.py     # Viewer session tracking
│   ├── watermark/
│   │   ├── common.py           # RS codec, HMAC RNG, FFmpeg utils
│   │   ├── layer1_visual.py    # Spread spectrum pixel watermark
│   │   ├── layer2_audio.py     # BPSK near-ultrasonic watermark
│   │   ├── layer3_dct.py       # DCT coefficient watermark
│   │   ├── embedder.py         # Full embedding pipeline
│   │   └── extractor.py        # Full extraction + attribution
└── hub/
    └── static/index.html       # Guardian unified dashboard
```
