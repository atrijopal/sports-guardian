# Sports Guardian — Demo Script

**URL:** https://kind-vibrancy-production-adf7.up.railway.app  
**Total time:** ~8 minutes

---

## Setup (do before the demo)

1. Have `match_clip.mp4` (45s+ sports clip) in `demo/m1-fingerprinting/original/`
2. Run attack generator to pre-make all attack videos
3. Have `broadcast.mp4` in `demo/m3-watermarking/source/`
4. Keep the Railway URL open in fullscreen

---

## Part 1 — Guardian Hub (30 sec)

**Open:** `/` (home page)

> "This is Sports Guardian — three modules that protect broadcast rights end to end. Detect a stolen clip, map the piracy network, trace the leaker."

Click through M1 → M2 → M3 cards briefly, then go back to Overview.

---

## Part 2 — Module 1: Signal Intercept (3 min)

**Open:** M1 tab

### Step 1 — Register the original
- Upload `match_clip.mp4` → Register
- Show it appears in the Vault with duration + fingerprint layers

> "We've registered a protected broadcast clip. Three fingerprints computed — visual, audio, and rhythm DNA."

### Step 2 — Check attacked clips (the money shots)

Upload each one, show the result:

| File | Expected | Talk track |
|---|---|---|
| `mirror.mp4` | ✅ MATCH | "Horizontally flipped — caught." |
| `muted.mp4` | ✅ MATCH | "Audio stripped — Layers 1 and 4 still catch it." |
| `speed_105.mp4` | ✅ MATCH | "5% faster — DNA encoding is speed-invariant." |
| `reencoded.mp4` | ✅ MATCH | "Fully re-encoded — pHash survives compression." |
| `unrelated.mp4` | ❌ NO MATCH | "Completely different content — correctly cleared." |

> "Five attacks, four catches, one correct clearance. The system doesn't over-flag."

---

## Part 3 — Module 2: War Room (2 min)

**Open:** M2 tab

> "While M1 identifies stolen clips, M2 watches where piracy is spreading right now."

Point out:
- **Live threat graph** — nodes are piracy domains, channels, accounts
- **CertStream counter** — new suspicious domains detected in real time
- **Operator clusters** — groups of domains run by the same pirate

Click a high-threat node → show the operator profile panel

> "Every new HTTPS certificate issued globally hits our scorer. Piracy sites get flagged before they've even posted their first stream."

Click **"Get AI Briefing"**

> "Gemini generates a structured threat assessment — level, top operators, which sports are most at risk, recommended actions."

---

## Part 4 — Module 3: Source Tracer (2 min)

**Open:** M3 tab

### Step 1 — Embed watermarks
Upload `broadcast.mp4` three times:

| Viewer Name | Account | What happens |
|---|---|---|
| Alice | ACC001 | alice_watermarked.mp4 generated |
| Bob | ACC002 | bob_watermarked.mp4 generated |
| Charlie | ACC003 | charlie_watermarked.mp4 generated |

> "Three viewers, three invisibly watermarked copies. Same video, different hidden identity."

Show the Session Registry filling up.

### Step 2 — The leak
- Download `bob_watermarked.mp4`
- Upload it to **Extract & Attribute** section

> "Someone leaked a clip. We don't know who. Let's find out."

Show result: **Bob identified** — account, region, platform, timestamp.

> "Three watermark layers survived the encode. Reed-Solomon error correction recovered the session ID. Bob leaked it."

---

## What Works / What Doesn't

### Works ✓
- M1: all visual attacks (mirror, crop, brightness, logo, re-encode)
- M1: speed changes up to ±20%
- M1: muted clips (Layers 1+4 compensate)
- M2: live CertStream threat graph, operator clustering, AI briefing
- M3: embed + extract on clean copies and lightly re-encoded copies

### Known limitations ✗
- M1: clips under 45s may produce weak DNA matches (Layer 4 needs events)
- M3: heavily re-encoded or screen-recorded clips may need multiple attempts
- M3: watermarked files are lost on Railway redeploy (stateless storage)
- M2: Gemini briefing requires API quota — falls back to Ollama if exhausted

---

## Backup plan if something breaks

| Problem | Fix |
|---|---|
| M1 no match on attacked video | Try `reencoded.mp4` — most reliable |
| M3 extraction fails | Re-embed fresh, use the downloaded file directly |
| M2 graph empty | Click Reset → graph repopulates with synthetic data |
| Gemini briefing fails | Module 2 still works — graph + certstream are the main demo |
