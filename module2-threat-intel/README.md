# Module 2 — Dark Social Intelligence Engine
### Digital Asset Protection · Piracy Threat Intelligence Dashboard

---

## What This Is

Module 2 answers the question: **"Who is running the piracy operation, and where is it being distributed?"**

It monitors Twitter, Reddit, Telegram, and real-time global DNS certificate registrations to find organized piracy networks distributing unauthorized sports streams. All collected data flows into a live threat graph that reveals operator clusters, infrastructure sharing, and lifecycle patterns.

This is the companion to Module 1 (video fingerprinting). Module 1 identifies *if* a video is pirated. Module 2 identifies *who did it* and *how they're organized*.

---

## What Was Built

### Project Structure

```
module2-threat-intel/
├── config.py                    # All API tokens, thresholds, tunables
├── app.py                       # FastAPI server + WebSocket + background tasks
├── graph_store.py               # In-memory graph with JSON persistence
├── scoring.py                   # Threat scores, cluster detection, lifecycle stages
├── nlp/
│   ├── classifier.py            # Gemini: post classification + entity extraction
│   └── domain_classifier.py    # Gemini: Tier 2 domain risk analysis queue
├── collectors/
│   ├── apify_twitter.py         # Twitter search via Apify Actor
│   ├── apify_reddit.py          # Reddit search via Apify Actor
│   ├── apify_telegram.py        # Telegram channel scraping via Apify Actor
│   ├── certstream_monitor.py    # Live Certificate Transparency monitor (Tier 1 + Tier 2)
│   └── fake_certstream.py       # Fallback: simulates certstream if blocked on demo network
├── parsers/
│   └── link_extractor.py        # Regex fallback: extract invite links and domains from text
├── scripts/
│   ├── generate_synthetic.py    # Generates 3 realistic operator clusters for demo
│   └── collect_data.py          # Pre-demo: runs all Apify collectors + NLP pipeline
├── static/
│   └── index.html               # Dashboard: vis.js graph + live certstream feed
├── data/
│   ├── graph.json               # Persisted graph (created at runtime)
│   └── raw/                     # Raw Apify JSON (for debugging)
└── requirements.txt
```

---

## How It Works — System Architecture

### The Five Components

#### 1. Apify Data Collectors (`collectors/apify_*.py`)
Uses Apify's pre-built scraper Actors (no Twitter/Reddit API keys needed) to search for piracy-related posts. Each collector:
- Calls the Apify Actor with search terms from `config.py`
- Saves raw JSON results to `data/raw/` for debugging
- Tries the NLP pipeline first; falls back to regex if NLP is unavailable
- Creates graph nodes for accounts and links, and edges for relationships

#### 2. NLP Intelligence Pipeline (`nlp/classifier.py`)
The core differentiator. Sends social media posts to Gemini in batches and gets back structured classifications. This catches what regex cannot:

| Post Text | Regex Finds | NLP Finds |
|-----------|-------------|-----------|
| "DM me for tonight's match 🔥" | Nothing | `intent=coded_distribution`, `threat=high`, signal: DM-distribution |
| "check my bio for the link" | Nothing | `intent=coded_distribution`, signal: bio-link |
| "usual place, same channel as last week" | Nothing | `intent=coded_distribution`, signal: coded-reference |
| "removed by mods, new link in comments" | Nothing | `intent=evasion`, signal: evasion-language |
| "Watch at streameast-hd.xyz" | domain extracted | domain + brand match + `threat=critical` |

For every piracy-related post, the NLP pipeline extracts:
- **Intent** — promotion, seeking, coded distribution, evasion
- **Entities** — domains, invite links, channels, accounts
- **Relationships** — who operates what, who mirrors who
- **Threat signals** — specific behaviors that indicate organized activity

All NLP metadata is stored on the graph node and shown in the dashboard side panel.

#### 3. Certstream Monitor — Two-Tier Architecture (`collectors/certstream_monitor.py`, `nlp/domain_classifier.py`)

Monitors the global Certificate Transparency feed (every new HTTPS certificate worldwide). Processes ~30 domains per second using two tiers:

```
Certstream WebSocket (~30 certs/sec)
    │
    ▼
TIER 1: Fast local scoring (Python thread, <1ms per domain)
    │ score < 3  → gray in feed bar, discard
    │ score >= 3 → pass to Tier 2 queue (~5% of domains)
    ▼
TIER 2: NLP batch (asyncio task, every 10 seconds)
    │ Drain up to 15 domains from queue
    │ Send batch to Gemini
    │ Gemini decodes: leetspeak, brand similarity, creative evasion
    │
    ├── NLP says "not suspicious" → discard
    └── NLP says "suspicious" → add to graph + pulse on dashboard
```

**Tier 1 scoring rules:**
- Contains streaming keyword (stream, sport, live, etc.) → +3 per keyword (max 2)
- Cheap TLD (.xyz, .top, .site, .online, .live, etc.) → +2
- Fuzzy match to known piracy brand → +4
- Domain name > 20 characters → +1
- Threshold ≥ 3 passes to Tier 2

**Why two tiers?** Claude costs money. You can't send 30 domains/second to the API (that's $50/hour). Tier 1 cuts 95% locally in <1ms. Only the suspicious 5% go to Claude. Result: ~6 NLP calls per minute, total demo cost under $2.

**Thread safety:** Certstream runs in a daemon thread. Three `queue.Queue` objects bridge the thread boundary to FastAPI's asyncio loop: `feed_queue` (all domains for scrolling bar), `tier2_queue` (suspicious domains for NLP), `notify_queue` (confirmed threats for graph).

#### 4. Graph Store (`graph_store.py`)
An in-memory graph backed by a JSON file. Key design decisions:
- **Deduplication on `(type, label)`** — if the same Twitter handle appears in synthetic data and real Apify data, they merge rather than duplicate
- **Atomic writes** — writes to a temp file then renames, preventing corruption on crash
- **No external database** — pure Python dict lookup; 100 nodes = microseconds

Node types: `domain`, `twitter_account`, `reddit_account`, `telegram_channel`, `invite_link`, `torrent`, `ip_address`

Edge relationship types: `posted`, `links_to`, `hosted_on`, `shared_in`, `resolves_to`, `same_operator`, `promotes`, `seeded_by`, `cross_posts`

#### 5. Scoring & Analysis (`scoring.py`)

Three analysis passes run after data collection and on graph reset:

**Threat Scores (0–100):**
```
score = normalize_to_100(
    0.4 × (connections / max_connections)   # more connected = more dangerous
  + 0.3 × exp(-hours_since_seen / 48)       # recent = more dangerous (exponential decay)
  + 0.3 × type_weight                       # domains > telegram > twitter > reddit
)
```

**Cluster Detection (union-find):**
Pairs of domain nodes are scored for "same operator" signals:
- Same TLD → +1
- Registered within 72 hours of each other → +2
- Domain names fuzzy-match (rapidfuzz > 75%) → +2
- Share a common neighbor (same Telegram channel) → +3
- Same IP address → +3

Score ≥ 4 merges them into a cluster. Transitive connections handled by union-find, so if A clusters with B and B clusters with C, all three form one cluster.

**Lifecycle Stages (domain nodes only):**
- `setup` — newly registered, no promotion activity yet
- `promotion` — has 1-2 promotion edges from social accounts
- `active` — 3+ promotion edges, or promoted across multiple platforms
- `dormant` — last_seen > 48 hours ago and was previously active

---

## The Dashboard (`static/index.html`)

Single-page, no framework, no build step. Loaded entirely in-browser.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ HEADER: title + live stats + CERTSTREAM LIVE badge      │
├──────────────────────────────────┬──────────────────────┤
│                                  │ SIDE PANEL (on click)│
│   vis.js Force-Directed Graph    │ - Threat score       │
│                                  │ - Lifecycle stage    │
│   Nodes colored by type          │ - NLP analysis       │
│   Sized by threat score          │ - Tier 2 NLP result  │
│   Clustered by operator          │ - Connections list   │
│                                  │ - Timeline           │
├──────────────────────────────────┴──────────────────────┤
│ LIVE FEED BAR: certstream domains scrolling in real time│
└─────────────────────────────────────────────────────────┘
```

**Graph configuration (vis.js):**
- Node colors and shapes differ by type (domain=diamond/red, Twitter=dot/blue, Telegram=triangle/green, etc.)
- Node size = `10 + (threat_score / 100) * 30` (range: 10px to 40px)
- `forceAtlas2Based` physics solver — handles 100+ nodes without lag
- Stabilizes in 200 iterations then physics disabled

**Live features:**
- WebSocket auto-reconnects on drop (2-second retry)
- New threat nodes animate in (size 0 → full size over 0.5s)
- Tier 2 NLP flagged domains pulse red in the feed bar
- Click any node → side panel shows all details including NLP metadata
- "Show Cluster" button highlights all nodes in an operator cluster
- Filter legend buttons hide/show by node type

---

## Synthetic Demo Data (`scripts/generate_synthetic.py`)

Generates a realistic pre-populated graph with 3 operator clusters:

**Cluster 1 — "The Streameast Network" (~30 nodes)**
A professional multi-domain operation. 4 mirror domains (registered within 48 hours of each other, same IP range), 3 Telegram channels, 5 Twitter accounts, 4 Reddit accounts, 3 invite links. Fully connected with `same_operator` edges between all domain pairs. One Twitter account has NLP metadata showing `coded_distribution` intent.

**Cluster 2 — "The Telegram Ring" (~15 nodes)**
A network of 6 Telegram channels that `cross_posts` to each other — coordinated sharing. 2 domains, 4 Twitter accounts, 3 invite links. Different topology from Cluster 1 (Telegram-centric vs domain-centric).

**Cluster 3 — "The Lone Wolf" (~8 nodes)**
A single 42,000-follower Twitter account that migrates domains. Shows the full lifecycle: 3 dormant domains + 1 active domain, registered over 2 weeks. Judges can see the migration pattern visually.

**Scattered independents (~15 nodes)**
5 low-follower Twitter accounts, 4 domain-only certstream flags (lifecycle=setup), 3 Reddit accounts. Makes the graph look realistic — not everything is neatly clustered.

After generation, `scoring.run_all_analysis()` computes threat scores, detects clusters, and assigns lifecycle stages automatically.

---

## Setup & Running

### Prerequisites
- Python 3.10+
- Internet connection (Apify API + Gemini API + certstream WebSocket)
- Apify account — free tier at [apify.com](https://apify.com), no credit card needed. Get token from Settings → Integrations
- Google Gemini API key — get free from [aistudio.google.com](https://aistudio.google.com). Free tier is sufficient for the entire demo.

### Install

```bash
cd module2-threat-intel
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Configure

Edit `config.py`:
```python
APIFY_API_TOKEN = "your_token_here"
GEMINI_API_KEY = "your_key_here"
NLP_ENABLED = True   # Set False for regex-only, zero API cost
```

### Prepare Demo Data

```bash
# Step 1: Generate synthetic graph (always run this first)
python scripts/generate_synthetic.py

# Step 2 (optional): Add real Apify data + NLP analysis
python scripts/collect_data.py
```

### Run

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard HTML |
| `GET` | `/api/graph` | Full graph (all nodes + edges) |
| `GET` | `/api/stats` | Node counts, clusters, NLP stats, certstream stats |
| `GET` | `/api/node/{id}` | Single node with edges, neighbors, velocity |
| `GET` | `/api/cluster/{id}` | All nodes and edges in an operator cluster |
| `GET` | `/api/certstream/stats` | Tier 1 + Tier 2 monitoring stats |
| `POST` | `/api/reset` | Clear graph and regenerate synthetic data |
| `POST` | `/api/collect` | Trigger Apify collection + NLP (testing only) |
| `WS` | `/ws/live` | WebSocket: `feed_domain`, `new_threat`, `stats_update` |

---

## Troubleshooting

**"Apify Actor failed"**
Open `data/raw/twitter_raw.json` (or reddit/telegram) and inspect the actual field names. The Actor IDs in `config.py` are best guesses — check [apify.com/store](https://apify.com/store) for alternatives if needed.

**"NLP classification failed"**
Check that `GEMINI_API_KEY` is set correctly. Set `NLP_ENABLED = False` to run in regex-only fallback mode (no cost, works fine for demo).

**"Certstream disconnected"**
The server auto-reconnects. If it keeps failing (firewall or certstream.calidog.io is down), the fake certstream fallback activates automatically and generates realistic synthetic domain alerts.

**"Graph looks cluttered"**
Adjust physics in `static/index.html`:
- Increase `gravitationalConstant` (more negative) to spread nodes further
- Increase `springLength` to stretch edges
- Decrease `springConstant` for looser clusters

**"No domains flagged by certstream"**
Lower `CERT_TIER1_FLAG_THRESHOLD` in `config.py` (try 2 instead of 3). Or wait — real certstream at 30 certs/second will hit a suspicious domain within minutes.

**"Tier 2 NLP not firing"**
Check that Tier 1 is passing domains: look at certstream stats in the header. If `Flagged` is 0, lower the threshold. If `Flagged` > 0 but Tier 2 isn't running, check the `GEMINI_API_KEY`.

---

## Technology Stack

| Layer | Tech | Why |
|-------|------|-----|
| Backend | FastAPI + Uvicorn | Async, WebSocket native, fast |
| Graph storage | In-memory dict + JSON | No Neo4j dependency, zero setup |
| Frontend | Vanilla JS + vis.js CDN | No build step, no npm, runs anywhere |
| Social scraping | Apify | No Twitter/Reddit API keys needed |
| NLP | Gemini (`gemini-2.0-flash`) | Catches coded language regex can't |
| Domain scoring | rapidfuzz (Tier 1) + Gemini (Tier 2) | Speed vs depth, cost-efficient |
| DNS live feed | certstream WebSocket | Real-time CT log, free, globally visible |
| Fuzzy matching | rapidfuzz | Fast brand-similarity without ML overhead |

---

## Cost Estimate (Full Demo)

| Operation | Estimated Cost |
|-----------|---------------|
| Pre-demo batch: ~500 social posts classified | ~$0.30–0.50 |
| Pre-demo: ~50 domains classified | ~$0.10 |
| Live certstream Tier 2 (15-min demo, ~60 domains) | ~$0.20–0.50 |
| **Total** | **< $1.50** |

Gemini free tier (Google AI Studio) covers the entire demo with no cost. Apify free tier ($5 credits) is more than sufficient.
