# Demo Videos Guide — Pile A & Pile B

---

## Pile A — Official Source Videos (you collect these)

**How many:** 3 videos minimum. 5 is ideal for a more impressive demo.

**Requirements for each video:**
- Duration: **≥ 60 seconds** (Layer 4 DNA needs at least 45s; 60s+ gives comfortable margin)
- Must have **audio** (commentary, crowd noise — anything works)
- Any resolution is fine; the system normalizes everything internally
- Format: MP4, MKV, AVI — FFmpeg handles all of them

**What kind of content:**
- Sports match footage (football, cricket, basketball — anything with action)
- Broadcast-style is best: varied motion, commentary audio, visible scoreboard/logo overlays

**Where to get free sports clips (legally):**

| Source | How to get it |
|--------|---------------|
| **YouTube** (your own uploads or CC-licensed) | Use [yt-dlp](https://github.com/yt-dlp/yt-dlp): `yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]" <URL>` |
| **Wikimedia Commons** | Search "sports" at commons.wikimedia.org — free to download |
| **Pexels / Pixabay** | pexels.com/videos and pixabay.com/videos — free sports stock clips |
| **Internet Archive** | archive.org — search for public domain sports broadcasts |
| **Your own phone footage** | Record a match, a TV screen, anything — it works |

> **Tip for yt-dlp on Windows:**
> ```
> pip install yt-dlp
> yt-dlp -f mp4 -o "demo_videos/%(title)s.%(ext)s" <YouTube-URL>
> ```
> Works on any YouTube video you have rights to use.

**Place all Pile A videos in:**
```
sports-fingerprint-demo/demo_videos/
```

---

## Pile B — Attacked Clips (auto-generated from Pile A)

**You do NOT collect these.** The `attack_generator.py` script creates them automatically from each Pile A video.

**Run it once per source video:**
```bash
cd sports-fingerprint-demo
python attack_generator.py demo_videos/match1.mp4
python attack_generator.py demo_videos/match2.mp4
python attack_generator.py demo_videos/match3.mp4
```

**What it generates (8 attacks per source video):**

| File suffix | Attack type | What it tests |
|-------------|-------------|----------------|
| `_attack_mirror.mp4` | Horizontal flip | Layer 1 mirror canonicalization |
| `_attack_crop70.mp4` | Center crop 70% | Layer 1 letterbox + crop normalization |
| `_attack_recolor.mp4` | Hue shift + saturation | Layer 1 histogram equalization |
| `_attack_speedup125.mp4` | 1.25× faster | Layer 4 DNA gap-ratio encoding |
| `_attack_muted.mp4` | Audio stripped | Layer 1 + 4 compensating for Layer 2 = 0% |
| `_attack_trim15s.mp4` | First 15 seconds only | All layers at lower confidence |
| `_attack_lowbitrate.mp4` | Heavy re-encode (200kbps) | Layer 1 + 2 robustness |
| `_attack_logo.mp4` | "PIRATE TV" text overlay | Layer 1 logo masking |

**Output location:**
```
sports-fingerprint-demo/demo_videos/attacks/
```

With 3 source videos, Pile B = **24 attacked clips**.
With 5 source videos, Pile B = **40 attacked clips**.

---

## Negative Controls (separate — not Pile A or B)

Keep **2–3 completely unrelated videos** that were never registered. Use these to prove the system has zero false positives.

- A random news clip, a movie trailer, a different sport entirely
- Check these last in the demo — judges expect to see NO MATCH

---

## Summary

| Pile | Who makes it | How many | Where |
|------|-------------|----------|-------|
| **A** — Source videos | You download/record | 3–5 | `demo_videos/` |
| **B** — Attacked clips | Auto-generated | 24–40 | `demo_videos/attacks/` |
| **Negatives** | You download | 2–3 | anywhere |
