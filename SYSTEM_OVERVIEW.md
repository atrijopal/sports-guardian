# Sports Guardian — System Overview

**Google Hackathon 2025 · Digital Asset Protection for Sports Media**  
Live: https://kind-vibrancy-production-adf7.up.railway.app

---

## Problem Statement

Sports broadcasters lose billions annually to piracy. Clips ripped from live streams are uploaded within minutes — mirrored, muted, re-encoded, cropped — making them hard to identify. Once uploaded, piracy networks spread them across Telegram, YouTube, and rogue domains. There is no reliable way to trace a leaked clip back to the viewer who recorded it.

Sports Guardian solves all three stages: **detect**, **map**, and **attribute**.

---

## System Architecture

```
Browser
  │
  ▼
main.py  ─── Railway ($PORT)
  │
  ├──  /          →  Guardian Hub (unified dashboard)
  ├──  /m1/*      →  Module 1 — Signal Intercept    (internal :8001)
  ├──  /m2/*      →  Module 2 — War Room            (internal :8002)
  ├──  /m3/*      →  Module 3 — Source Tracer       (internal :8003)
  └──  /ws/live   →  WebSocket proxy → Module 2
```

A single FastAPI process (`main.py`) acts as the entry point. It launches all three modules as subprocesses on internal ports and reverse-proxies all traffic. The browser sees one URL, one port.

---

## Module 1 — Signal Intercept (Video Fingerprinting)

**Question it answers:** *"Is this stolen from our broadcast?"*

### Pipeline

A suspect clip is compared against all registered originals using three independent layers. Each layer produces a score between 0 and 1. A final fusion step combines them.

---

#### Layer 1 — Visual pHash

1. FFmpeg extracts one frame every 2 seconds from both videos
2. Each frame is normalized:
   - Black letterbox bars are detected and stripped
   - Frame is center-cropped to a square
   - Resized to 256×256
   - Logo mask applied (top-left and bottom-right corners blanked — typical watermark zones)
   - Histogram equalized to remove brightness/contrast attacks
3. A 64-bit perceptual hash (pHash) is computed — nearby images produce similar hashes
4. **Mirror canonicalization:** both the frame and its horizontal flip are hashed. The lexicographically smaller hash is stored. This makes a mirrored video produce the same fingerprint as the original.
5. Match score = fraction of suspect frames whose nearest hash in the original is within Hamming distance 12

**Robust to:** mirroring, re-encoding, brightness changes, logo overlays, letterboxing

---

#### Layer 2 — Audio Chromaprint

1. FFmpeg extracts audio as 44.1 kHz mono WAV
2. `fpcalc -raw` (Chromaprint) converts audio to a sequence of 32-bit integers — a compact acoustic fingerprint
3. **Sliding-window XOR matching:** the suspect's fingerprint is slid across the original's fingerprint, computing the average number of differing bits per integer at each offset. The minimum across all offsets is the distance.
4. Score = 1.0 if distance < threshold, 0.0 if muted (graceful fallback)

**Robust to:** re-encoding, bitrate changes, compression artifacts  
**Limitation:** returns 0.0 for muted clips — Layers 1 and 4 compensate

---

#### Layer 4 — Match DNA

1. 1-Hz visual energy signal extracted: mean absolute frame difference per second
2. 1-Hz audio RMS signal extracted: root mean square energy per second
3. `scipy.signal.find_peaks` detects significant events (peaks) in both signals
4. Peaks are encoded as a "DNA string": `V` for visual peak, `A` for audio peak, separated by gap buckets (`s` < 3s, `m` 3–8s, `l` > 8s)
   - Example: `VsAmVlA`
5. `rapidfuzz.fuzz.partial_ratio` does fuzzy **substring** matching — the suspect's DNA is searched within the original's DNA
6. Gap buckets are ratios, not absolute times → speed changes (±20%) don't break the match

**Robust to:** speed changes, audio replacement, any attack that preserves the broadcast rhythm

---

#### Fusion

```
overall_score = 0.45 × L1 + 0.35 × L2 + 0.20 × L4

MATCH  if  overall_score ≥ 0.55  AND  at least 2 layers individually agree
```

Returns: verdict (`MATCH` / `NO_MATCH` / `INCONCLUSIVE`), per-layer scores, explanation string, matched video name.

---

## Module 2 — War Room (Threat Intelligence)

**Question it answers:** *"Where is piracy spreading right now?"*

### Real-Time Data Ingestion

**CertStream** monitors the global SSL certificate transparency log — every new HTTPS certificate issued anywhere in the world appears within seconds. Each new domain is scored instantly:

| Check | Points |
|---|---|
| Contains piracy keywords (stream, live, free, sport…) | +3 |
| Cheap TLD (.xyz, .top, .stream, .live…) | +2 |
| Fuzzy-matches known piracy brands (streameast, crackstream…) | +4 |
| Unusually long domain name | +1 |

Domains scoring ≥ 3 are flagged and queued for deeper analysis.

**Apify scrapers** collect from Twitter, Reddit, and Telegram for piracy promotion links.

---

### Three-Tier Scoring

| Tier | Method | Latency |
|---|---|---|
| 1 | Keyword + TLD + brand fuzzy match | Milliseconds |
| 2 | Gemini AI classifies whether domain is a piracy site | Seconds (batched) |
| 3 | Google Safe Browsing API v4 confirms malware/phishing | Real-time |

---

### Threat Graph

All entities (domains, YouTube channels, Telegram channels, Twitter accounts, Reddit accounts, invite links) are nodes. Relationships (promotes, links_to, same_operator, posted) are edges.

**Operator clustering** uses Union-Find to link domains by:
- Same TLD registered within 72 hours
- Shared promotion channels
- Brand name similarity > 75%
- Shared IP ranges

**Threat score** per node:
```
score = 0.4 × connections + 0.3 × recency_decay + 0.3 × node_type_weight
recency_decay = e^(−hours_since_last_seen / 48)
```

**Lifecycle stages:** `setup → promotion → active → dormant`

---

### AI Intelligence

- **Threat briefing** (every 30 min): Gemini generates a structured JSON assessment — threat level, top threats, cluster analysis, sports at risk, recommended actions
- **Operator profiles**: on-demand natural language intelligence profile for any node
- **YouTube hunt** (every 15 min): automated search for piracy channels using configurable query sets
- **Fallback**: Ollama (`llama3.1:8b`) used automatically when Gemini quota is exhausted

---

## Module 3 — Source Tracer (Watermarking)

**Question it answers:** *"Who leaked this clip?"*

### Concept

Every time a viewer gets access to a stream, they receive a uniquely watermarked copy. The watermark is invisible and inaudible. If that copy leaks, uploading it to Source Tracer reveals the session ID — identifying the exact viewer, account, region, and platform.

### Embedding Pipeline

Three independent layers embed the same 64-bit session ID simultaneously:

---

#### Layer 1 — Spread Spectrum Visual

- Every 5th frame is modified
- An HMAC-SHA256 keyed pseudo-random number generator (seeded with frame number + secret key) selects 32×32 pixel blocks
- A pseudo-random noise pattern scaled to ±4 intensity is added to each block
- Invisible to the human eye; detectable by correlation

---

#### Layer 2 — BPSK Audio

- Watermark bits are encoded as **Binary Phase Shift Keying** at 19 kHz carrier frequency (near-ultrasonic — above most audio content)
- Each bit: 50ms at 0° phase (bit=1) or 180° phase (bit=0)
- Pattern repeats every 10 seconds
- Detection: bandpass filter (18–20.5 kHz) + coherent correlation against reference carrier

---

#### Layer 3 — DCT Coefficient Modulation

- Each frame divided into 8×8 DCT blocks
- HMAC-seeded RNG selects 6 blocks per bit
- The parity of a mid-frequency DCT coefficient (4,3) is forced to encode the bit
- Quantization step of 15 ensures the modification survives moderate compression

---

#### Reed-Solomon Error Correction

All three layers protect the 64-bit session ID with 10 Reed-Solomon error correction symbols (using `reedsolo`). This tolerates up to 5 byte errors per layer — covering re-encoding, partial corruption, and screen recording artifacts.

---

#### Extraction & Attribution

1. Upload suspect clip
2. All three layers independently attempt to extract the session ID
3. Results are majority-voted across layers
4. Matched against the session registry → returns viewer name, account ID, region, platform, IP, embed timestamp

---

## Guardian Hub

A unified dashboard that embeds all three modules in an iframe-based single-page interface. Tab navigation lazy-loads each module. Status pings check all three modules on load and every 30 seconds.

---

## Deployment

### Architecture

Single Railway service. `main.py` is the entry point — it starts M1, M2, M3 as background subprocesses on internal ports 8001/8002/8003, then reverse-proxies all HTTP traffic and WebSocket connections to them. Railway sees one process, one port.

### Build

`nixpacks.toml` installs FFmpeg and Chromaprint (fpcalc) as system packages. `requirements.txt` combines all module dependencies into a single Python environment.

### Configuration

API keys set as environment variables:

| Variable | Used by |
|---|---|
| `GEMINI_API_KEY` | M1 AI analysis, M2 threat briefings |
| `YOUTUBE_API_KEY` | M1 YouTube scan, M2 channel hunting |
| `SAFE_BROWSING_API_KEY` | M2 domain threat confirmation |

---

## Tech Stack

| Component | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Reverse proxy | httpx (async HTTP client) |
| Video processing | FFmpeg |
| Audio fingerprinting | Chromaprint / fpcalc |
| Visual hashing | imagehash (pHash) |
| Computer vision | OpenCV (headless) |
| Audio analysis | librosa, soundfile |
| Signal processing | scipy |
| Fuzzy matching | rapidfuzz |
| Error correction | reedsolo (Reed-Solomon) |
| Threat graph | Custom in-memory GraphStore + JSON persistence |
| Certificate monitoring | certstream-python |
| AI / LLM | Google Gemini 2.0 Flash · Ollama llama3.1:8b (fallback) |
| Safe Browsing | Google Safe Browsing API v4 |
| YouTube | YouTube Data API v3 |
| Frontend | Vanilla JS · vis-network · Chakra Petch + Azeret Mono |
| Real-time | WebSocket (FastAPI native) |
| Deployment | Railway (single service, Nixpacks build) |

---

## Known Limitations

- **Layer 4 (DNA)** needs clips ≥ 45 seconds to produce enough events for reliable matching
- **Layer 2 (Audio)** returns 0.0 for muted clips — by design; Layers 1 and 4 compensate
- **Storage** is JSON file-backed with brute-force search — suitable for < 20 demo videos
- **Watermarking** on Railway is stateless between restarts — sessions reset on redeploy
- **Layer 3 (Motion)** is referenced in the architecture but not built — Layers 1, 2, 4 cover the demo

---

*Sports101 · Google Hackathon 2025*
