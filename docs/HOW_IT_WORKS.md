# How the Fingerprinting System Works

---

## The Core Problem

A pirate takes an official sports video, applies a few tricks — mirrors it, strips the audio, slaps a logo on it, speeds it up — and reuploads it. A simple hash (MD5, SHA-256) breaks the moment a single pixel changes. Our system doesn't care about pixels. It cares about **identity**.

---

## Step 1 — Pre-Normalization (Before Any Fingerprinting)

Before any layer even looks at a frame, every frame goes through a **normalization pipeline** that strips out all the cheap tricks pirates use.

```
Raw Frame
    │
    ▼
Strip Letterbox        ← Remove black bars (top/bottom/left/right)
    │
    ▼
Center Crop Square     ← Take central 80% — mild cropping attacks become a no-op
    │
    ▼
Grayscale + Resize     ← Convert to grayscale, resize to 256×256
    │
    ▼
Mask Logo Corners      ← Black out top-left and bottom-right 15% squares
    │
    ▼
Histogram Equalize     ← Flatten brightness/contrast — kills recoloring attacks
    │
    ▼
Canonical Frame        ← Ready for hashing
```

**Mirror canonicalization** is handled separately: for every frame, we compute the hash of both the frame AND its horizontal flip, then store only the **lexicographically smaller** one. This means a mirrored video produces identical hashes to the original — the attack is a no-op.

---

## Layer 1 — Visual Fingerprint (pHash)

### How the fingerprint is made

1. FFmpeg extracts one frame every 2 seconds from the video
2. Each frame goes through the normalization pipeline above
3. A **perceptual hash (pHash)** is computed — an 8×8 = 64-bit hash that captures the visual structure of the frame, not its exact pixels
4. The hash is stored alongside its timestamp

### How matching works

For each frame in the **suspect clip**, we find the closest matching frame in the **original** by computing **Hamming distance** (count of differing bits between two 64-bit hashes).

- If the distance is ≤ 12 bits (out of 64), it counts as a match
- Final score = fraction of suspect frames that found a match
- If fewer than 30% of frames match, score is forced to 0.0

### What it survives

| Attack | Why it survives |
|--------|----------------|
| Mirror | Mirror canonicalization (min hash trick) |
| Crop | Center crop normalization removes edge differences |
| Logo overlay | Logo corners are masked out before hashing |
| Recolor / brightness | Histogram equalization makes all frames look the same tonally |
| Re-encode / compression | pHash is perceptual — small pixel noise doesn't change the hash |

### What it struggles with

- Heavy speed changes (frames land at different timestamps, fewer matches)
- Very short clips (fewer frames = less evidence)

---

## Layer 2 — Audio Fingerprint (Chromaprint)

### How the fingerprint is made

1. FFmpeg extracts the audio as a 44.1kHz mono WAV
2. **fpcalc** (Chromaprint — same tech as Shazam) processes the audio and outputs a list of **32-bit integers** that encode the acoustic structure of the audio over time
3. This list is stored as the audio fingerprint

### How matching works

We use a **sliding window** approach:

```
Original:  [int1, int2, int3, int4, int5, int6, int7, int8, ...]
Suspect:               [int1, int2, int3, int4]       ← slide across

At each offset, compute average XOR bit distance between overlapping ints.
Best offset = position where suspect audio most closely matches original.
```

- Score = `1.0 - (best_avg_bits / 32)`
- If the best match still has > 10 differing bits on average, score = 0.0

This handles **trimmed clips** — a clip starting at minute 3 of an original will still match because the window slides to find where it fits.

### What it survives

| Attack | Why it survives |
|--------|----------------|
| Trimming | Sliding window finds the right offset |
| Re-encode | Chromaprint is robust to compression artifacts |
| Logo overlays / cropping | Audio is untouched |

### What it struggles with

- **Muted clips** — no audio = score is 0.0 (by design, not a bug). Layers 1 and 4 compensate.
- Heavy pitch shifting or audio replacement

---

## Layer 4 — Match DNA (Event Sequence Fingerprinting)

This is the headline layer. No other system does this.

### The idea

Instead of looking at pixels or audio waveforms, we look at the **rhythm of the broadcast** — when exciting things happen. A goal, a foul, a crowd roar, a fast camera cut. These events happen at fixed points in time regardless of whether someone mirrored the video or changed the colors.

### How the fingerprint is made

**Step 1 — Extract 1-Hz energy signals**

Two signals are computed, one sample per second:

- **Visual energy**: mean absolute pixel difference between consecutive 1-fps frames. High value = fast motion or cut.
- **Audio energy**: RMS (root mean square) amplitude of the audio in each 1-second window. High value = loud crowd or commentary spike.

**Step 2 — Detect peaks**

`scipy.signal.find_peaks` finds moments where energy spikes above background noise (prominence threshold = 0.15 on a 0–1 normalized signal). These are the **events** — the moments that define the broadcast.

**Step 3 — Encode as a DNA string**

Events are sorted by time and encoded as characters:
- `V` = visual energy peak (motion/cut)
- `A` = audio energy peak (crowd/commentary)

The **gap between consecutive events** is quantized into buckets:
- `s` = short gap (< 3 seconds)
- `m` = medium gap (3–8 seconds)
- `l` = long gap (> 8 seconds)

Example DNA string: `VsAmVlAsVmA`

```
V  s  A  m  V  l  A  s  V  m  A
│  │  │  │  │  │  │  │  │  │  │
│  │  │  │  │  │  │  │  │  └──┴── audio peak after medium gap
│  │  │  │  │  │  │  └────────── visual peak after short gap
│  │  │  │  │  └──────────────── audio peak after long gap
│  │  │  └────────────────────── visual peak after medium gap
│  │  └──────────────────────── audio peak after short gap
│  └────────────────────────── short gap
└───────────────────────────── visual peak
```

**Why gap buckets and not exact seconds?**
A 1.25× sped-up video compresses a 5-second gap to 4 seconds. If we stored exact seconds, it would break. Buckets are **relative** — a medium gap stays medium whether the video is sped up or slowed down by 25%.

### How matching works

We use **fuzzy substring matching** via `rapidfuzz.fuzz.partial_ratio`:

- The suspect's DNA string is searched for inside the original's DNA string
- "Partial" means we look for the suspect as a **substring** of the original — this handles trimmed clips
- The fuzzy part handles minor encoding differences

Score = `partial_ratio / 100`. If below 70, score = 0.0.

### What it survives

| Attack | Why it survives |
|--------|----------------|
| Speed change (±25%) | Gap bucket encoding absorbs the time compression |
| Mirror / crop / recolor | Events are based on energy, not pixel values |
| Logo overlay | Doesn't affect motion or audio energy |
| Audio replacement / muting | Visual energy channel still fires independently |
| Trimming | Fuzzy substring search finds the clip within the original |

---

## Fusion — Combining the Layers

Each layer returns a score from 0.0 to 1.0. The fusion layer combines them:

```
Overall Score = (Layer1 × 0.45) + (Layer2 × 0.35) + (Layer4 × 0.20)
```

Two conditions must both be true for a **MATCH**:
1. Overall score ≥ 0.55
2. At least 2 layers individually agree (L1 ≥ 0.35, L2 ≥ 0.50, L4 ≥ 0.60)

The second condition prevents a single very strong layer from forcing a false positive when the others are silent.

### Example: muted clip

| Layer | Score | Agrees? |
|-------|-------|---------|
| Layer 1 (Visual) | 0.88 | Yes |
| Layer 2 (Audio) | 0.00 | No — audio stripped |
| Layer 4 (DNA) | 0.74 | Yes |
| **Overall** | **0.655** | **MATCH** |

The system correctly identifies the clip even though Layer 2 is completely blind.

### Example: sped-up clip

| Layer | Score | Agrees? |
|-------|-------|---------|
| Layer 1 (Visual) | 0.52 | Yes (weakened — frames at different timestamps) |
| Layer 2 (Audio) | 0.45 | No (pitch/timing shift degrades it) |
| Layer 4 (DNA) | 0.78 | Yes (gap buckets absorbed the speed change) |
| **Overall** | **0.587** | **MATCH** |

Layer 4 saves the match.

---

## End-to-End Flow

```
REGISTER
────────
Upload video
    │
    ├─► Layer 1: extract frames every 2s → normalize → pHash each frame
    ├─► Layer 2: extract audio WAV → fpcalc → list of Chromaprint ints
    └─► Layer 4: extract 1fps frames + audio → energy signals → peaks → DNA string
    │
    └─► Store all three fingerprints in fingerprints_db.json


CHECK
─────
Upload suspect clip
    │
    ├─► Generate Layer 1 + 2 + 4 fingerprints (same pipeline)
    │
    └─► Compare against every registered video:
            Layer 1: Hamming distance on frame hashes
            Layer 2: Sliding window XOR distance on Chromaprint ints
            Layer 4: rapidfuzz partial_ratio on DNA strings
            Fusion:  Weighted score + agreeing layers check
    │
    └─► Return best match with per-layer breakdown and explanation
```

---

## Why Three Layers?

No single layer catches everything:

| Attack | L1 Visual | L2 Audio | L4 DNA |
|--------|-----------|----------|--------|
| Mirror | ✓ | ✓ | ✓ |
| Crop | ✓ | ✓ | ✓ |
| Recolor | ✓ | ✓ | ✓ |
| Speed change | Weak | Weak | **✓** |
| Muted | ✓ | ✗ | ✓ |
| Trim | ✓ | ✓ | ✓ |
| Low bitrate | ✓ | ✓ | ✓ |
| Logo overlay | ✓ | ✓ | ✓ |

The system is designed so that **any two layers agreeing is enough** to call a match. Pirates would need to simultaneously defeat the visual structure, the acoustic fingerprint, AND the broadcast rhythm — which is effectively impossible without destroying the content itself.
