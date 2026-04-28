# Sports Guardian

**Multi-layer sports media Digital Asset Protection platform.**  
Video fingerprinting · Real-time piracy intelligence · Invisible watermarking

Built for the Google Hackathon 2025.

---

## What It Does

Sports Guardian is a three-module system that protects live sports broadcast rights end-to-end:

| Module | Role |
|---|---|
| **Signal Intercept** (M1) | Identifies whether a suspect clip was ripped from a protected broadcast, surviving mirroring, re-encoding, muting, speed changes, logo overlays, and cropping |
| **War Room** (M2) | Real-time piracy intelligence dashboard — monitors SSL certificate transparency logs, clusters piracy operators, hunts YouTube channels, runs AI threat briefings |
| **Source Attribution** (M3) | Embeds invisible per-viewer watermarks into video streams so leaked footage can be traced back to the exact subscriber |

---

## Live Demo

Deployed as a single service on Railway. All three modules are accessible from one URL:

| Path | Module |
|---|---|
| `/` | Guardian Hub — unified dashboard |
| `/m1/` | Signal Intercept — video fingerprinting |
| `/m2/` | War Room — threat intelligence |
| `/m3/` | Source Attribution — watermarking |

---

## Architecture

```
                    Railway (single service)
                    ┌──────────────────────────────────┐
  Browser ──────▶  │  main.py  (:$PORT)               │
                   │  ├── /        → Hub UI            │
                   │  ├── /m1/*   → M1 (internal :8001)│
                   │  ├── /m2/*   → M2 (internal :8002)│
                   │  ├── /m3/*   → M3 (internal :8003)│
                   │  └── /ws/live → M2 WebSocket      │
                   └──────────────────────────────────┘
```

`main.py` is the single entry point. It starts M1, M2, and M3 as background subprocesses and reverse-proxies all traffic to them.

---

## Module 1 — Signal Intercept (Video Fingerprinting)

Identifies pirated clips using a three-layer pipeline robust to:
- Mirror / horizontal flip
- Re-encoding at different bitrates
- Muting or audio replacement
- Speed changes (±20%)
- Letterbox cropping, logo overlays, brightness shifts

**Layer 1 — Visual pHash:** Extracts frames via FFmpeg, normalizes each (letterbox strip → center crop → grayscale → logo mask → histogram equalization), computes 64-bit pHash. Mirror canonicalization stores the smaller of `hash(frame)` and `hash(flipped_frame)`.

**Layer 2 — Audio Chromaprint:** Extracts 44.1 kHz mono audio, runs through `fpcalc -raw`, then uses sliding-window XOR distance matching to locate the suspect clip within the original fingerprint. Returns 0.0 for muted clips.

**Layer 4 — Match DNA:** Extracts 1-Hz visual and audio energy signals, detects peaks with `scipy`, encodes them as a DNA string with quantized gaps. Fuzzy substring match via `rapidfuzz`. Speed invariant.

**Fusion:**
```
overall = 0.45 × L1 + 0.35 × L2 + 0.20 × L4
match   = overall ≥ 0.55  AND  agreeing_layers ≥ 2
```

---

## Module 2 — War Room (Threat Intelligence)

**Data ingestion:** CertStream monitors the global SSL certificate transparency log in real time. Every new certificate is scored against keyword lists, cheap TLD lists, and brand similarity checks. Apify scrapers collect from Twitter, Reddit, and Telegram.

**Three-tier domain scoring:**
1. Keyword scoring, TLD penalty, brand fuzzy match
2. AI classification of flagged domains
3. Google Safe Browsing API confirmation

**Threat graph:** Nodes (domains, YouTube channels, Telegram, Twitter, Reddit) connected by edges. Union-Find operator clustering.

**AI intelligence:** Gemini-powered threat briefings every 30 minutes, per-node operator profiles, YouTube piracy channel hunting.

---

## Module 3 — Source Attribution (Watermarking)

Embeds a 64-bit session ID invisibly into video. Survives re-encoding, compression, and screen recording.

**Layer 1 — Spread Spectrum Visual:** Pseudo-random noise patterns in 32×32 pixel blocks every 5th frame. HMAC-SHA256 keyed RNG per frame.

**Layer 2 — BPSK Audio:** Watermark bits encoded as Binary Phase Shift Keying at 19 kHz carrier, repeated every 10 seconds.

**Layer 3 — DCT Coefficient Modulation:** 8×8 DCT blocks with forced mid-frequency coefficient parity encoding.

All three layers use Reed-Solomon error correction (10 symbols, tolerates 5 byte errors per layer). Upload a suspect clip → layers vote → session ID resolved → viewer identified.

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
| AI intelligence | Gemini API · Ollama llama3.1:8b (fallback) |
| Safe Browsing | Google Safe Browsing API v4 |
| YouTube intel | YouTube Data API v3 |
| Frontend | Vanilla JS, vis-network, Chakra Petch + Azeret Mono |
| Real-time comms | WebSocket (FastAPI) |

---

## Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com)

1. Fork this repo
2. Create a new Railway project → **Deploy from GitHub repo** → select this repo
3. Leave root directory blank — Railway auto-detects `nixpacks.toml`
4. Add environment variables (see Configuration below)
5. **Generate Domain** → your app is live

Railway installs FFmpeg and Chromaprint automatically via Nixpacks. All three modules run as a single service.

---

## Run Locally

**Prerequisites:** Python 3.11+, FFmpeg, fpcalc in PATH

```bash
# Install dependencies
pip install -r requirements.txt

# Start everything
uvicorn main:app --reload

# Open http://localhost:8000
```

---

## Configuration

Add API keys as environment variables in Railway (or a local `.env`):

| Variable | Used by | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | M1, M2 | AI analysis + threat briefings |
| `YOUTUBE_API_KEY` | M1, M2 | YouTube scan + piracy hunt |
| `SAFE_BROWSING_API_KEY` | M2 | Google Safe Browsing |

Set them in each module's `config.py` locally, or as Railway environment variables for deployment.

---

## Project Structure

```
sports-guardian/
├── main.py                     # Single entry point — launches all modules
├── requirements.txt            # Combined dependencies
├── nixpacks.toml               # Railway build config (ffmpeg + chromaprint)
├── module1-fingerprinting/
│   ├── app.py                  # FastAPI routes
│   ├── config.py               # Thresholds + API keys
│   ├── storage.py              # JSON fingerprint DB
│   └── fingerprint/
│       ├── layer1_visual.py
│       ├── layer2_audio.py
│       ├── layer4_dna.py
│       └── fusion.py
├── module2-threat-intel/
│   ├── app.py                  # FastAPI + WebSocket + background tasks
│   ├── config.py               # Scoring weights + API keys
│   ├── graph_store.py          # Threat graph
│   ├── scoring.py              # Threat scores + clustering
│   ├── google_services.py      # Safe Browsing, YouTube, Gemini
│   └── collectors/             # CertStream, Apify scrapers
├── module3-watermarking/
│   ├── app.py                  # FastAPI routes
│   ├── config.py               # Watermark parameters
│   ├── session_registry.py     # Viewer session tracking
│   └── watermark/              # Embed + extract pipeline
└── hub/
    └── static/index.html       # Guardian unified dashboard
```
