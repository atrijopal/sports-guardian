# Module 2 — Dark Social Intelligence Engine
## Hackathon Demo Implementation Plan (for Claude Code)

---

## 0. Read This First (Context for Claude Code)

You are building a **piracy threat intelligence dashboard** that monitors Twitter, Reddit, Telegram, and new domain registrations to find organized piracy networks distributing unauthorized sports streams.

This is **Module 2** of a larger "Digital Asset Protection" system. Module 1 (fingerprinting) answers "is this video pirated?" — Module 2 answers **"who did it and where is it being distributed?"**

This is NOT a scraper project. The scraping is done by Apify (a third-party API). You are building:
1. A data pipeline that calls Apify, parses results, and builds a threat graph
2. An NLP intelligence pipeline (Claude Sonnet API) that classifies posts, detects coded piracy language, extracts entities, and infers relationships — far beyond what regex can catch
3. A live certstream monitor that detects new suspicious domains in real time (with NLP-powered Tier 2 classification)
4. A visual dashboard that renders the threat graph and lets judges explore it interactively

**This is a hackathon demo.** Optimize for:
1. **Visual impact** — the graph visualization IS the demo. If it looks boring, nothing else matters.
2. **One live moment** — certstream running on stage, new domains appearing in real time
3. **Coherent story** — 3 operator clusters that judges can click through and understand
4. **Reliability** — no Neo4j, no Redis, no external databases. In-memory Python + JSON file.
5. **Windows compatibility** — target machine is Windows 10/11
6. **~10 hour build budget**

**The target demo experience:**
- Dashboard loads with a pre-populated threat graph of 80–120 nodes
- Nodes are colored by type (domains, Twitter accounts, Telegram channels, Reddit accounts, invite links)
- Node size reflects threat score
- Judges can click any node to see its connections, history, and threat details
- Three visible operator clusters with shared infrastructure highlighted
- A live feed panel showing certstream domains scrolling in real time
- When a suspicious domain is detected live, it appears on the graph with a pulse animation
- Side panel shows lifecycle stage, threat score, and connection timeline for selected nodes

---

## 1. What the System Does (Broader View)

### The Problem
Pirated sports streams don't appear from nowhere. Behind every illegal stream is an **operation**: someone registers throwaway domains, promotes them via Telegram channels and Twitter accounts, cross-posts invite links on Reddit, and migrates to new domains when old ones get taken down. Individual takedowns are whack-a-mole. To stop piracy at scale, you need to map the **network** — find the operators, not just the links.

### The Solution
A threat intelligence system with four data collection components feeding into a central graph that reveals piracy networks:

**Component 1 — Link Surface Crawler:** Scans aggregator websites that list illegal streams. *(Simulated with mock data for demo — building a full JS-rendering crawler is out of scope.)*

**Component 2 — Invite Link Harvester (via Apify):** Searches Twitter, Reddit, and Telegram for public posts containing invite links to piracy groups (t.me/, discord.gg/, chat.whatsapp.com/). Uses Apify's pre-built scrapers — no API keys from Twitter/Reddit needed.

**Component 3 — DNS Shadow Tracker (Certstream):** Monitors the global Certificate Transparency log feed in real time. Every new HTTPS certificate worldwide is checked against piracy domain patterns. This is the LIVE component that runs on stage.

**Component 4 — Torrent DHT Monitor:** Passively monitors BitTorrent's DHT network for sports-related torrents. *(Simulated with mock data for demo — DHT protocol implementation is out of scope.)*

**Component 5 — Threat Graph Dashboard:** All data converges into a graph where nodes are entities (accounts, domains, channels, links) and edges are relationships (posted, hosts, shared, resolves_to). Graph algorithms compute threat scores, detect operator clusters, and track lifecycle stages.

### Why This Wins
- **NLP-powered intelligence** — Claude Sonnet classifies piracy intent, detects coded language ("DM me", "check bio", "usual place"), and infers operator relationships from natural language. No other team will have this.
- Real data from Apify (not obviously fake)
- Live certstream on stage (genuinely impressive)
- Graph visualization tells a story judges can explore
- Operator clustering reveals organized networks, not just individual links
- Lifecycle tracking shows the system can predict threats ("detected 4 hours before stream went live")

---

## 2. Tech Stack (All Free or Near-Free)

**Language:** Python 3.10+

**Python packages:**
- `fastapi` — web backend
- `uvicorn[standard]` — ASGI server
- `apify-client` — calls Apify Actors for Twitter/Reddit/Telegram scraping
- `anthropic` — Claude Sonnet API for NLP intelligence pipeline
- `certstream` — real-time Certificate Transparency WebSocket feed
- `rapidfuzz` — fuzzy domain name matching (Tier 1 fast filter for certstream)
- `dnspython` — DNS lookups for domain enrichment
- `python-multipart` — FastAPI dependency
- `websockets` — certstream dependency

**Frontend (loaded from CDN in HTML, no npm):**
- `vis-network` — force-directed graph visualization (https://unpkg.com/vis-network/standalone/umd/vis-network.min.js)
- Vanilla HTML/CSS/JS — no React, no build step

**Storage:** In-memory Python dictionaries + JSON file persistence. NO Neo4j, NO PostgreSQL, NO Redis.

**External services:**
- Apify free tier ($5/month credits, no credit card) — for Twitter/Reddit/Telegram scraping
- Anthropic API (Claude Sonnet) — for NLP classification, entity extraction, relationship inference. Cost for entire demo: ~$1-2 total. Use model `claude-sonnet-4-20250514`.
- certstream.calidog.io — free WebSocket feed of Certificate Transparency logs

**NLP cost budget:**
- Pre-demo batch classification of ~500 posts: ~$0.30-0.50
- Pre-demo domain classification of ~50 domains: ~$0.10
- Live certstream Tier 2 during 15-min demo: ~$0.50-1.00
- Total NLP spend: under $2 for the entire hackathon

---

## 3. Project Structure

Create exactly this structure:

```
module2-threat-intel/
├── requirements.txt
├── README.md
├── config.py                        # API tokens, scoring thresholds, all tunables
├── app.py                           # FastAPI server + WebSocket for live updates
├── graph_store.py                   # In-memory graph with JSON persistence
├── scoring.py                       # Threat scores, clustering, lifecycle stages
├── nlp/
│   ├── __init__.py
│   ├── classifier.py                # Claude Sonnet: post classification + entity extraction
│   └── domain_classifier.py         # Claude Sonnet: domain name risk analysis (Tier 2)
├── collectors/
│   ├── __init__.py
│   ├── apify_twitter.py             # Search Twitter via Apify Actor
│   ├── apify_reddit.py              # Search Reddit via Apify Actor
│   ├── apify_telegram.py            # Scrape Telegram channels via Apify Actor
│   └── certstream_monitor.py        # Live Certificate Transparency monitor (Tier 1 + Tier 2)
├── parsers/
│   ├── __init__.py
│   └── link_extractor.py            # FALLBACK: regex extraction when NLP is unavailable
├── scripts/
│   ├── collect_data.py              # Pre-demo: run all Apify collectors + NLP pipeline
│   └── generate_synthetic.py        # Generate realistic synthetic data for demo
├── static/
│   └── index.html                   # Dashboard with vis.js graph + live feed
└── data/
    ├── graph.json                   # Persisted graph (created at runtime)
    └── raw/                         # Raw Apify JSON results (for debugging)
```

---

## 4. Config File (`config.py`)

All tunable parameters in one place:

```python
# config.py

# ---- Apify ----
APIFY_API_TOKEN = ""  # User fills this in. Free tier, no credit card.

# Apify Actor IDs (these are real Actor IDs from Apify Store)
# User should verify these are still active before demo.
# If an Actor doesn't work, find an alternative on apify.com/store
APIFY_TWITTER_ACTOR = "apidojo/tweet-scraper"
APIFY_REDDIT_ACTOR = "trudax/reddit-scraper"
APIFY_TELEGRAM_ACTOR = "danielmilevski9/telegram-channel-scraper"

# ---- Twitter Search Queries ----
TWITTER_QUERIES = [
    "football stream t.me/",
    "soccer live stream discord.gg/",
    "match free stream link",
    "sports stream telegram",
    "football live free HD",
]
TWITTER_MAX_ITEMS_PER_QUERY = 30

# ---- Reddit Search ----
REDDIT_SUBREDDITS = [
    "https://www.reddit.com/r/soccer/",
    "https://www.reddit.com/r/sports/",
    "https://www.reddit.com/r/football/",
]
REDDIT_SEARCH_TERMS = ["free stream", "live stream link", "watch free"]
REDDIT_MAX_ITEMS = 50

# ---- Telegram Channels ----
# Public channels to monitor. Use real public channels that discuss
# sports/streaming. These are examples — find active ones before demo.
TELEGRAM_CHANNELS = [
    "@sportsnews",
    "@footballupdates",
]
TELEGRAM_MAX_MESSAGES = 100

# ---- Certstream Domain Scoring (Tier 1 — fast local filter) ----
CERT_KEYWORDS = ["stream", "sport", "live", "hd", "free", "match",
                  "watch", "football", "soccer", "cricket", "nba",
                  "ufc", "boxing", "fpl"]
CERT_CHEAP_TLDS = [".xyz", ".top", ".site", ".online", ".live",
                    ".stream", ".club", ".fun", ".icu", ".buzz"]
CERT_KNOWN_BRANDS = ["streameast", "sportsurge", "crackstream",
                      "buffstream", "720pstream", "markkystream",
                      "methstream", "weakspell", "sportshd"]
CERT_SCORE_KEYWORD = 3
CERT_SCORE_CHEAP_TLD = 2
CERT_SCORE_BRAND_SIMILARITY = 4
CERT_SCORE_LONG_DOMAIN = 1     # domain name > 20 chars
CERT_TIER1_FLAG_THRESHOLD = 3  # Tier 1 passes domain to Tier 2 NLP queue
CERT_TIER2_BATCH_INTERVAL = 10 # seconds between Tier 2 NLP batch calls
CERT_TIER2_MAX_BATCH = 15      # max domains per NLP batch call

# ---- NLP Pipeline (Claude Sonnet) ----
ANTHROPIC_API_KEY = ""  # User fills this in.
NLP_MODEL = "claude-sonnet-4-20250514"
NLP_MAX_TOKENS = 1500
NLP_BATCH_SIZE = 15            # posts per API call for classification
NLP_ENABLED = True             # Set False to fall back to regex-only mode
NLP_TEMPERATURE = 0.0          # deterministic output for classification

# ---- Threat Scoring ----
THREAT_WEIGHT_CONNECTIONS = 0.4    # more connections = higher threat
THREAT_WEIGHT_RECENCY = 0.3       # more recent activity = higher threat
THREAT_WEIGHT_TYPE = 0.3           # domains score higher than tweets
THREAT_TYPE_WEIGHTS = {
    "domain": 1.0,
    "telegram_channel": 0.8,
    "twitter_account": 0.6,
    "reddit_account": 0.5,
    "invite_link": 0.7,
    "torrent": 0.6,
    "ip_address": 0.4,
}

# ---- Clustering ----
CLUSTER_SAME_TLD_WINDOW_HOURS = 72     # domains registered within N hours
CLUSTER_SHARED_CHANNEL_THRESHOLD = 2   # linked to same channel = cluster
CLUSTER_BRAND_SIMILARITY_THRESHOLD = 75 # rapidfuzz score for domain names

# ---- Lifecycle ----
LIFECYCLE_STAGES = {
    "setup": {"color": "#6b7280", "label": "Setup"},
    "promotion": {"color": "#f59e0b", "label": "Promotion"},
    "active": {"color": "#ef4444", "label": "Active"},
    "dormant": {"color": "#374151", "label": "Dormant"},
}

# ---- Paths ----
GRAPH_DATA_PATH = "data/graph.json"
RAW_DATA_DIR = "data/raw"

# ---- Server ----
HOST = "0.0.0.0"
PORT = 8000
```

---

## 5. Module-by-Module Build Order

Build in this exact order. Each checkpoint gives you a working demo at increasing levels of impressiveness.

### Checkpoint 1: Dashboard skeleton with hardcoded graph (2 hours)
1. Create folder structure
2. Write `requirements.txt`
3. Write `config.py`
4. Write `graph_store.py` with in-memory graph and JSON persistence
5. Write minimal `app.py` serving `static/index.html`
6. Write `static/index.html` with vis.js loaded from CDN
7. Hardcode 15 nodes and 12 edges in a test JSON file
8. Render the graph with colored nodes, sized by a dummy threat score
9. Add click-to-select: clicking a node shows its details in a side panel
10. **Verify:** page loads, graph renders, nodes are clickable, side panel shows info

### Checkpoint 2: Synthetic data fills the graph (1.5 hours)
1. Write `scripts/generate_synthetic.py` — creates 3 operator clusters + scattered nodes
2. Write `scoring.py` — threat score computation, cluster detection, lifecycle tagging
3. Run synthetic generator, load graph, verify ~80-100 nodes render well
4. Tune vis.js physics so the graph settles quickly and clusters are visible
5. **Verify:** graph looks impressive, clusters are visually distinct, threat scores vary

### Checkpoint 3: Regex fallback + Apify pipeline brings real data (2 hours)
1. Write `parsers/link_extractor.py` — regex patterns for invite links and domains (FALLBACK)
2. Write `collectors/apify_twitter.py` — search Twitter, parse results, create nodes/edges
3. Write `collectors/apify_reddit.py` — search Reddit, parse results, create nodes/edges
4. Write `collectors/apify_telegram.py` — scrape channels, parse results, create nodes/edges
5. Write `scripts/collect_data.py` — orchestrates all 3 collectors using regex extraction
6. Run `collect_data.py` once with real Apify token, verify real data mixes into graph
7. **Verify:** real Twitter/Reddit/Telegram data appears alongside synthetic data. Regex extraction works.

### Checkpoint 4: NLP Intelligence Pipeline — THE DIFFERENTIATOR (2 hours)
1. Write `nlp/classifier.py` — Claude Sonnet batch classification of posts
2. Write `nlp/domain_classifier.py` — Claude Sonnet domain risk analysis
3. Update `scripts/collect_data.py` to try NLP pipeline first, fall back to regex
4. Run collect_data.py again — verify NLP produces richer entities and relationships
5. Verify posts with coded language ("DM me", "check bio") now get flagged
6. Verify NLP-inferred relationships create new edges in the graph
7. **Verify:** NLP output is visibly richer than regex. Side panel shows NLP confidence, intent, threat signals.

### Checkpoint 5: Certstream goes live with Tier 1 + Tier 2 (1.5 hours)
1. Write `collectors/certstream_monitor.py` — Tier 1 fast local scoring + Tier 2 NLP queue
2. Wire certstream into `app.py` as a background thread + asyncio queue bridge
3. Wire Tier 2 NLP batch processing as a periodic asyncio task (every 10s)
4. Add WebSocket endpoint in FastAPI to push live domain alerts to the frontend
5. Add live feed panel to `index.html` — scrolling domains, Tier 2 flagged ones highlighted
6. When a domain is flagged by NLP Tier 2, add it to graph with pulse animation
7. **Verify:** start server, watch domains scroll by, see Tier 1 quick flags AND Tier 2 NLP flags

### Checkpoint 6: Polish the dashboard (1 hour)
1. Add operator cluster highlighting — click a cluster label, all its nodes glow
2. Add lifecycle stage indicators — color coding on domain nodes
3. Add timeline view in side panel — chronological list of events for selected node
4. Add overall stats bar: "142 entities tracked | 3 networks | 12 flagged today | NLP: 47 posts classified"
5. Add NLP insight badge on nodes that were NLP-classified (show confidence, intent, signals)
6. Style everything for stage: dark theme, monospace numbers, subtle glow effects
7. **Verify:** full demo flow works end-to-end, looks polished on a projector

### Checkpoint 7: Final testing (0.5 hours)
1. Run the full demo script 3 times
2. Verify certstream doesn't crash after 5 minutes of running
3. Verify NLP calls don't timeout or error during live certstream
4. Verify graph doesn't lag with 100+ nodes
5. Verify click interactions work smoothly
6. Test with NLP_ENABLED=False to confirm regex fallback works
7. Prepare demo talking points

---

## 6. Detailed Specs — Module by Module

### 6.1 `graph_store.py` — In-Memory Graph with JSON Persistence

This is the core data structure. Everything reads from and writes to this.

**Data model:**

```python
# A node in the graph
{
    "id": "node_uuid4",
    "type": "domain" | "twitter_account" | "reddit_account" |
            "telegram_channel" | "invite_link" | "torrent" | "ip_address",
    "label": "streameast-hd.xyz",          # display name
    "metadata": {
        # type-specific fields:
        # For domain:
        "tld": ".xyz",
        "registrar": "Namecheap",
        "cert_issuer": "Let's Encrypt",
        "ip": "104.21.x.x",
        "is_live": True,
        "dns_records": ["A: 104.21.x.x"],

        # For twitter_account:
        "handle": "@streamking2024",
        "followers": 12400,
        "verified": False,

        # For telegram_channel:
        "channel_name": "@sportstreams_hd",
        "subscribers": 45000,

        # For reddit_account:
        "username": "u/streamguy99",
        "karma": 2300,

        # For invite_link:
        "url": "https://t.me/sportstreams_hd",
        "platform": "telegram",

        # For torrent:
        "info_hash": "abc123...",
        "name": "EPL Match Day 12 720p",
        "size_mb": 1200,
    },
    "first_seen": "ISO-8601",
    "last_seen": "ISO-8601",
    "threat_score": 0.0,           # computed by scoring.py, 0-100
    "lifecycle_stage": "setup",    # setup|promotion|active|dormant
    "cluster_id": None,            # operator cluster assignment
    "source": "apify_twitter" | "apify_reddit" | "apify_telegram" |
              "certstream" | "synthetic" | "mock_crawler" | "mock_dht",
    "is_real_data": True,          # True if from Apify/certstream, False if synthetic
}

# An edge in the graph
{
    "id": "edge_uuid4",
    "source": "node_id_1",
    "target": "node_id_2",
    "relationship": "posted" | "links_to" | "hosted_on" | "shared_in" |
                     "resolves_to" | "same_operator" | "promotes" |
                     "seeded_by" | "cross_posts",
    "timestamp": "ISO-8601",
    "metadata": {}  # optional extra info
}
```

**Functions to implement:**

```python
class GraphStore:
    def __init__(self, persist_path: str):
        """Load graph from JSON file if it exists, else start empty."""
        self.nodes: dict[str, dict] = {}   # id -> node
        self.edges: dict[str, dict] = {}   # id -> edge
        self.persist_path = persist_path

    def add_node(self, node: dict) -> str:
        """
        Add a node. If a node with the same (type, label) already exists,
        MERGE: update last_seen, merge metadata, don't duplicate.
        Return the node id (existing or new).
        """

    def add_edge(self, edge: dict) -> str:
        """
        Add an edge. If an identical (source, target, relationship) edge
        exists, update timestamp but don't duplicate.
        Return the edge id.
        """

    def get_node(self, node_id: str) -> dict | None:
        """Return a single node by id."""

    def get_edges_for_node(self, node_id: str) -> list[dict]:
        """Return all edges where this node is source or target."""

    def get_neighbors(self, node_id: str) -> list[dict]:
        """Return all nodes connected to this node."""

    def get_all_nodes(self) -> list[dict]:
        """Return all nodes."""

    def get_all_edges(self) -> list[dict]:
        """Return all edges."""

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        """Return all nodes of a given type."""

    def get_nodes_by_cluster(self, cluster_id: str) -> list[dict]:
        """Return all nodes in a given operator cluster."""

    def get_stats(self) -> dict:
        """
        Return summary stats:
        {
            "total_nodes": 112,
            "total_edges": 187,
            "nodes_by_type": {"domain": 23, "twitter_account": 31, ...},
            "clusters": 3,
            "flagged_today": 12,
        }
        """

    def find_node(self, node_type: str, label: str) -> dict | None:
        """Find a node by type and label (for deduplication)."""

    def save(self):
        """Persist to JSON file. Call after any mutation."""

    def load(self):
        """Load from JSON file."""

    def reset(self):
        """Clear all data. For demo reset."""
```

**Critical implementation notes:**
- The `add_node` deduplication is important. When Apify returns a Twitter user who already exists in the graph (from synthetic data or a previous run), merge don't duplicate. Match on `(type, label)`.
- `save()` should write atomically (write to temp file, then rename) to prevent corruption if the process crashes mid-write.
- Keep it simple. This is a dict lookup, not a database. 100 nodes = microseconds.

### 6.2 `parsers/link_extractor.py` — Extract Structured Data from Raw Text

**Purpose:** Given raw text (a tweet, Reddit comment, Telegram message), extract all invite links, streaming domains, and relevant patterns.

```python
import re
from urllib.parse import urlparse

# Regex patterns for invite links
INVITE_PATTERNS = [
    r'(https?://t\.me/[\w+]+)',                    # Telegram
    r'(https?://telegram\.me/[\w+]+)',              # Telegram alt
    r'(https?://discord\.gg/[\w]+)',                # Discord
    r'(https?://discord\.com/invite/[\w]+)',        # Discord alt
    r'(https?://chat\.whatsapp\.com/[\w]+)',        # WhatsApp
]

# Regex for general URLs
URL_PATTERN = r'(https?://[^\s<>"\']+)'

# Keywords that suggest a URL is streaming-related
STREAM_KEYWORDS = ["stream", "live", "watch", "free", "hd", "match",
                    "sport", "football", "soccer", "cricket", "m3u8"]

def extract_invite_links(text: str) -> list[dict]:
    """
    Find all invite links in text.
    Return list of:
    {
        "url": "https://t.me/sportstreams",
        "platform": "telegram" | "discord" | "whatsapp",
        "group_id": "sportstreams"  # extracted from URL
    }
    """

def extract_domains(text: str) -> list[dict]:
    """
    Find all URLs in text, extract their domains.
    Filter to only domains that look streaming-related
    (contain stream keywords or use cheap TLDs).
    Return list of:
    {
        "url": "https://streameast-hd.xyz/live/football",
        "domain": "streameast-hd.xyz",
        "tld": ".xyz",
        "is_suspicious": True,
        "matched_keywords": ["stream", "hd"]
    }
    """

def extract_all(text: str) -> dict:
    """
    Run all extractors on text.
    Return {
        "invite_links": [...],
        "domains": [...],
        "raw_urls": [...]    # all URLs found, for reference
    }
    """
```

**Important:** Be generous with extraction. It's better to extract a non-piracy URL and filter later than to miss an actual invite link. The graph can handle noise; missing data is worse.

### 6.3 `nlp/classifier.py` — NLP Post Classification & Entity Extraction (Claude Sonnet)

**Purpose:** The core intelligence engine. Takes raw social media posts, sends them to Claude Sonnet in batches, and gets back structured classifications with entity extraction and relationship inference. This catches everything regex misses: coded language, indirect promotion, evasion tactics, and implicit relationships.

**Why this exists:** Real piracy promotion is sneaky. Posts like "DM me for tonight's match 🔥⚽", "check my bio for the link", "usual place, same channel as last week", or "removed by mods, new link in comments" contain ZERO URLs. Regex extracts nothing. Claude classifies all of them correctly.

```python
import json
from anthropic import Anthropic
import config

# Initialize client once at module level
_client = None

def _get_client() -> Anthropic:
    """Lazy-init the Anthropic client. Returns None if no API key."""
    global _client
    if _client is None and config.ANTHROPIC_API_KEY:
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client

# ---- System prompts ----

POST_CLASSIFICATION_PROMPT = """You are a piracy intelligence analyst working for a sports rights protection organization. You analyze social media posts to detect piracy-related activity.

Given a batch of social media posts, analyze EACH post and return a JSON array where each element corresponds to one post (same order as input).

For each post, return:
{
  "post_index": 0,
  "is_piracy_related": true/false,
  "confidence": 0.0-1.0,
  "intent": "promotion" | "seeking" | "discussion" | "evasion" | "coded_distribution" | "unrelated",
  "entities": [
    {"text": "extracted text", "type": "domain|invite_link|channel|account|brand|sport_event", "value": "normalized value"}
  ],
  "relationships": [
    {"source": "entity_value_1", "target": "entity_value_2", "type": "promotes|operates|mirrors|cross_posts|same_operator|admin_of"}
  ],
  "threat_signals": [],
  "threat_level": "none" | "low" | "medium" | "high" | "critical",
  "summary": "one sentence explanation"
}

Detection rules — be aggressive:
- "DM me", "PM me", "message me for link" = coded_distribution (HIGH threat)
- "check bio", "link in bio", "link in profile" = coded_distribution (HIGH threat)
- "usual place", "same channel", "you know where" = coded_distribution (HIGH threat)
- "removed by mods", "taken down", "new link" = evasion (HIGH threat)
- Keywords with sports context: "stream", "live", "free", "HD", "watch" = promotion if combined with a sport
- Invite link patterns (t.me/, discord.gg/, chat.whatsapp.com/) = always extract as entities
- Any domain URLs = extract and flag if they contain streaming keywords
- Account mentions (@handle, u/username) = extract as entities
- If a post mentions one entity operating/managing/running another, extract that as a relationship
- If a post implies two domains are mirrors or run by the same person, extract a "same_operator" relationship

Return ONLY the JSON array. No markdown, no explanation, no preamble."""

DOMAIN_CLASSIFICATION_PROMPT = """You are a domain intelligence analyst. You evaluate newly registered domain names to determine if they are likely related to sports piracy/illegal streaming.

Given a batch of domain names, analyze EACH and return a JSON array:

{
  "domain_index": 0,
  "domain": "str3am-eastHD.xyz",
  "is_suspicious": true/false,
  "confidence": 0.0-1.0,
  "risk_level": "none" | "low" | "medium" | "high" | "critical",
  "reasons": ["leetspeak for 'stream'", "matches brand 'streameast'", "cheap TLD .xyz"],
  "category": "streaming_piracy" | "gambling" | "phishing" | "legitimate" | "other" | "unknown",
  "similar_to_brands": ["streameast"],
  "decoded_name": "stream east HD"
}

Detection rules:
- Leetspeak: "str3am" = "stream", "sp0rt" = "sport", "fr33" = "free", "l1ve" = "live"
- Character insertion: "s-t-r-e-a-m" or "s.p.o.r.t.s" = evasion
- Known piracy brand variations: streameast, sportsurge, crackstream, buffstream, 720pstream, markkystream, methstream, weakspell, sportshd
- Cheap TLDs: .xyz, .top, .site, .online, .live, .stream, .club, .fun, .icu, .buzz
- Suspicious patterns: sport+stream+free combinations, "watch" + sport name, "hd" + sport
- False positive awareness: "sportswear-shop.com" is NOT piracy. Context matters.

Return ONLY the JSON array. No markdown, no explanation."""


def classify_posts(posts: list[dict]) -> list[dict]:
    """
    Classify a batch of social media posts using Claude Sonnet.

    Args:
        posts: list of dicts, each with at minimum:
            {"text": "...", "source": "twitter|reddit|telegram", "author": "..."}

    Returns:
        list of classification dicts (same order as input), or empty list on failure.

    Implementation:
    1. Check if NLP is enabled (config.NLP_ENABLED) and client is available.
       If not, return empty list (caller falls back to regex).
    2. Format the posts into a numbered list for the prompt:
       "Post 0 [twitter/@streamking]: DM me for tonight's match..."
       "Post 1 [reddit/u/sportsfan99]: anyone got a working link?..."
    3. Call Claude Sonnet with POST_CLASSIFICATION_PROMPT as system,
       formatted posts as user message.
    4. Parse the JSON response. Handle malformed JSON gracefully:
       - Strip ```json fences if present
       - Try json.loads()
       - If parsing fails, log error and return empty list
    5. Validate that returned array length matches input length.
       If not, log warning and pad/truncate.
    6. Return the classification array.

    CRITICAL ERROR HANDLING:
    - Wrap the entire function in try/except.
    - If Anthropic API is unreachable, rate-limited, or returns error:
      log the error and return empty list. NEVER crash.
    - The caller MUST handle empty returns by falling back to regex.
    - Log every API call's token usage for cost tracking.

    BATCHING:
    - If len(posts) > NLP_BATCH_SIZE, split into chunks and make
      multiple API calls. Combine results.
    - Each batch should be independent (no cross-references between batches).
    """

    client = _get_client()
    if not client or not config.NLP_ENABLED:
        return []

    results = []
    # Split into batches
    for i in range(0, len(posts), config.NLP_BATCH_SIZE):
        batch = posts[i:i + config.NLP_BATCH_SIZE]
        try:
            # Format posts for prompt
            formatted = "\n\n".join([
                f"Post {j} [{p.get('source', 'unknown')}/{p.get('author', 'unknown')}]: {p.get('text', '')}"
                for j, p in enumerate(batch)
            ])

            response = client.messages.create(
                model=config.NLP_MODEL,
                max_tokens=config.NLP_MAX_TOKENS,
                temperature=config.NLP_TEMPERATURE,
                system=POST_CLASSIFICATION_PROMPT,
                messages=[{"role": "user", "content": formatted}]
            )

            # Extract text from response
            text = response.content[0].text
            text = text.strip().removeprefix("```json").removesuffix("```").strip()
            batch_results = json.loads(text)

            if isinstance(batch_results, list):
                results.extend(batch_results)
            else:
                print(f"[WARNING] NLP returned non-list: {type(batch_results)}")

            # Log usage
            print(f"[NLP] Classified {len(batch)} posts. "
                  f"Tokens: {response.usage.input_tokens}in/{response.usage.output_tokens}out")

        except json.JSONDecodeError as e:
            print(f"[ERROR] NLP JSON parse failed: {e}")
            # Continue with next batch, don't crash
        except Exception as e:
            print(f"[ERROR] NLP API call failed: {e}")
            # Continue with next batch

    return results


def classify_domains(domains: list[str]) -> list[dict]:
    """
    Classify a batch of domain names using Claude Sonnet (Tier 2).

    Args:
        domains: list of domain name strings, e.g. ["str3am-east.xyz", "example.com"]

    Returns:
        list of classification dicts (same order as input), or empty list on failure.

    Implementation:
    1. Check NLP enabled + client available.
    2. Format domains as numbered list.
    3. Call Claude with DOMAIN_CLASSIFICATION_PROMPT.
    4. Parse JSON response.
    5. Return classifications.

    Same error handling as classify_posts: never crash, return [] on failure.
    """


def process_nlp_results_to_graph(
    posts: list[dict],
    nlp_results: list[dict],
    graph,  # GraphStore
    source_platform: str
) -> dict:
    """
    Take NLP classification results and create graph nodes + edges.

    For each classified post where is_piracy_related == True:
    1. Create a node for the post author (twitter_account, reddit_account, etc.)
       Include NLP metadata: confidence, intent, threat_level, threat_signals
    2. For each entity extracted by NLP:
       - type "domain" → create domain node
       - type "invite_link" → create invite_link node
       - type "channel" → create telegram_channel node
       - type "account" → create appropriate account node
       - type "brand" → check if brand matches existing nodes, link them
    3. For each relationship extracted by NLP:
       - Create an edge between the two entities
       - relationship types map to edge types:
         "promotes" → "promotes" edge
         "operates" → "same_operator" edge
         "mirrors" → "same_operator" edge
         "same_operator" → "same_operator" edge
    4. Always create "posted" edge from author → each entity they mentioned

    For posts where is_piracy_related == False:
       Skip entirely. Don't pollute the graph with noise.

    Return stats: {"nodes_created": N, "edges_created": M, "posts_flagged": K}

    IMPORTANT: Store the NLP classification on the node metadata so the
    dashboard can display it:
      node["metadata"]["nlp_confidence"] = 0.92
      node["metadata"]["nlp_intent"] = "coded_distribution"
      node["metadata"]["nlp_threat_signals"] = ["DM-based distribution", "coded language"]
      node["metadata"]["nlp_summary"] = "Account uses DM-based distribution..."
    """
```

**How classify_posts handles the posts regex would miss:**

| Post text | Regex finds | NLP finds |
|-----------|-------------|-----------|
| "DM me for tonight's match 🔥⚽" | Nothing | intent=coded_distribution, threat=high, signal=DM-distribution |
| "check my bio for the link" | Nothing | intent=coded_distribution, threat=high, signal=bio-link |
| "usual place, same channel as last week" | Nothing | intent=coded_distribution, threat=high, signal=coded-reference |
| "removed by mods, new link in comments" | Nothing | intent=evasion, threat=high, signal=evasion-language |
| "Watch at streameast-hd.xyz" | domain: streameast-hd.xyz | domain + intent=promotion + brand=streameast + threat=critical |
| "Admin of @sportshd moved to soccerfree.xyz" | URL + mention | entities + relationship: admin_of(@sportshd → soccerfree.xyz) + same_operator |

This table is your strongest demo moment. Show it on a slide: "Here's what regex finds. Here's what our NLP pipeline finds."

### 6.4 `nlp/domain_classifier.py` — NLP Domain Risk Analysis (Certstream Tier 2)

**Purpose:** Receives batched domain names from the certstream Tier 1 filter and runs deep NLP analysis to catch evasion techniques (leetspeak, character insertion, creative naming) that simple keyword matching misses.

```python
from nlp.classifier import classify_domains

class DomainClassifierQueue:
    """
    Manages the Tier 2 NLP queue for certstream domains.

    Certstream Tier 1 (fast, local) filters ~95% of domains instantly.
    The ~5% that pass Tier 1 go into this queue.
    Every CERT_TIER2_BATCH_INTERVAL seconds, this queue drains up to
    CERT_TIER2_MAX_BATCH domains and sends them to Claude for deep analysis.

    Thread safety: uses a thread-safe queue since certstream runs in
    a separate thread.
    """

    def __init__(self):
        self.pending = []  # thread-safe: use queue.Queue in actual impl
        self.results = []  # recently classified domains
        self.stats = {
            "domains_queued": 0,
            "domains_classified": 0,
            "domains_flagged_tier2": 0,
        }

    def enqueue(self, domain: str, tier1_score: int, tier1_reasons: list[str]):
        """
        Add a domain to the Tier 2 queue with its Tier 1 context.
        Called from the certstream thread — must be thread-safe.
        """

    async def process_batch(self, graph, notify_callback=None):
        """
        Called periodically (every CERT_TIER2_BATCH_INTERVAL seconds)
        by the FastAPI asyncio loop.

        1. Drain up to CERT_TIER2_MAX_BATCH domains from the queue
        2. Call classify_domains() with the batch
        3. For each domain classified as suspicious by NLP:
           a. Create a domain node in the graph with NLP metadata
           b. Call notify_callback to push to WebSocket clients
           c. Include NLP analysis in the node: decoded_name,
              similar_to_brands, risk_level, reasons
        4. Update stats

        The node metadata should include BOTH Tier 1 and Tier 2 info:
          node["metadata"]["tier1_score"] = 5
          node["metadata"]["tier1_reasons"] = ["keyword: stream", "cheap TLD"]
          node["metadata"]["tier2_risk"] = "high"
          node["metadata"]["tier2_reasons"] = ["leetspeak: str3am=stream", "brand match: streameast"]
          node["metadata"]["tier2_decoded_name"] = "stream east HD"
          node["metadata"]["tier2_confidence"] = 0.91

        The dashboard displays both tiers — judges can see the two-stage analysis.
        """
```

### 6.5 `collectors/apify_twitter.py` — Twitter Search via Apify

**Purpose:** Search Twitter for tweets containing streaming keywords and invite link patterns, then parse results using NLP (with regex fallback) into graph nodes and edges.

```python
from apify_client import ApifyClient
from parsers.link_extractor import extract_all
from graph_store import GraphStore
import config
import json
import os
from datetime import datetime

def search_twitter(graph: GraphStore) -> dict:
    """
    Search Twitter via Apify for each query in config.TWITTER_QUERIES.
    For each tweet found:
      1. Create a twitter_account node for the author
      2. Extract invite links and domains from tweet text
      3. Create invite_link / domain nodes for each extracted item
      4. Create "posted" edges from account to each link/domain
      5. Save raw results to data/raw/twitter_raw.json for debugging

    Returns summary: {"tweets_processed": N, "nodes_created": M, "edges_created": K}

    CRITICAL ERROR HANDLING:
    - If APIFY_API_TOKEN is empty, log warning and return empty results.
      Do NOT crash. The demo can run on synthetic data alone.
    - If an Actor fails (timeout, rate limit, wrong Actor ID), catch the
      exception, log it, and continue with the next query.
    - If a tweet has no text (deleted, restricted), skip it silently.
    - Save whatever partial results you got before the error.
    """

    if not config.APIFY_API_TOKEN:
        print("[WARNING] No Apify token configured. Skipping Twitter collection.")
        return {"tweets_processed": 0, "nodes_created": 0, "edges_created": 0}

    client = ApifyClient(config.APIFY_API_TOKEN)
    all_results = []
    stats = {"tweets_processed": 0, "nodes_created": 0, "edges_created": 0}

    for query in config.TWITTER_QUERIES:
        try:
            run = client.actor(config.APIFY_TWITTER_ACTOR).call(input={
                "searchTerms": [query],
                "maxItems": config.TWITTER_MAX_ITEMS_PER_QUERY,
                "sort": "Latest",
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            all_results.extend(items)
        except Exception as e:
            print(f"[ERROR] Twitter query '{query}' failed: {e}")
            continue

    # Save raw results
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    with open(os.path.join(config.RAW_DATA_DIR, "twitter_raw.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # ---- NLP-FIRST APPROACH ----
    # Try NLP pipeline first. If it fails or is disabled, fall back to regex.
    #
    # Step 1: Prepare posts for NLP
    posts_for_nlp = []
    for tweet in all_results:
        author_handle = _extract_author_handle(tweet)
        text = tweet.get("text") or tweet.get("full_text") or ""
        if author_handle and text:
            posts_for_nlp.append({
                "text": text,
                "source": "twitter",
                "author": author_handle,
                "followers": _extract_followers(tweet),
                "verified": tweet.get("isVerified", False),
                "_raw_tweet": tweet,  # keep reference for metadata
            })

    # Step 2: Try NLP classification
    from nlp.classifier import classify_posts, process_nlp_results_to_graph
    nlp_results = classify_posts(posts_for_nlp)

    if nlp_results and len(nlp_results) > 0:
        # NLP succeeded — use rich classification
        print(f"[NLP] Successfully classified {len(nlp_results)} tweets")
        nlp_stats = process_nlp_results_to_graph(
            posts_for_nlp, nlp_results, graph, "twitter"
        )
        stats["tweets_processed"] = nlp_stats.get("posts_flagged", 0)
        stats["nodes_created"] = nlp_stats.get("nodes_created", 0)
        stats["edges_created"] = nlp_stats.get("edges_created", 0)
    else:
        # NLP failed or disabled — fall back to regex extraction
        print("[FALLBACK] NLP unavailable, using regex extraction for Twitter")
        for post in posts_for_nlp:
            tweet = post["_raw_tweet"]
            author_handle = post["author"]
            text = post["text"]

            # Create author node
            author_node_id = graph.add_node({
                "type": "twitter_account",
                "label": author_handle,
                "metadata": {
                    "handle": author_handle,
                    "followers": post["followers"],
                    "verified": post["verified"],
                },
                "first_seen": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "source": "apify_twitter",
                "is_real_data": True,
            })
            stats["nodes_created"] += 1

            # Regex extraction (fallback)
            extracted = extract_all(text)

            for invite in extracted["invite_links"]:
                link_node_id = graph.add_node({
                    "type": "invite_link",
                    "label": invite["url"],
                    "metadata": {"url": invite["url"], "platform": invite["platform"]},
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "source": "apify_twitter",
                    "is_real_data": True,
                })
                graph.add_edge({
                    "source": author_node_id,
                    "target": link_node_id,
                    "relationship": "posted",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["nodes_created"] += 1
                stats["edges_created"] += 1

            for domain_info in extracted["domains"]:
                domain_node_id = graph.add_node({
                    "type": "domain",
                    "label": domain_info["domain"],
                    "metadata": {
                        "tld": domain_info["tld"],
                        "matched_keywords": domain_info.get("matched_keywords", []),
                    },
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "source": "apify_twitter",
                    "is_real_data": True,
                })
                graph.add_edge({
                    "source": author_node_id,
                    "target": domain_node_id,
                    "relationship": "promotes",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["nodes_created"] += 1
                stats["edges_created"] += 1

            stats["tweets_processed"] += 1

    graph.save()
    return stats


def _extract_author_handle(tweet: dict) -> str | None:
    """
    Extract author handle from tweet. Apify Actors have inconsistent
    field names. Try common patterns:
      tweet["author"]["userName"]
      tweet["user"]["screen_name"]
      tweet["username"]
      tweet["authorName"]
    Return "@handle" or None.
    """

def _extract_followers(tweet: dict) -> int:
    """
    Extract follower count. Try:
      tweet["author"]["followers"]
      tweet["user"]["followers_count"]
      tweet["authorFollowers"]
    Return int or 0.
    """
```

**CRITICAL NOTE ON APIFY ACTOR FIELD NAMES:**
Different Apify Actors return different JSON structures. After your first successful run, open `data/raw/twitter_raw.json` and inspect the actual field names. Then update `_extract_author_handle` and `_extract_followers` to match. Do NOT assume the field names above are correct — they are best guesses. The raw JSON is your source of truth.

### 6.4 `collectors/apify_reddit.py` — Reddit Search via Apify

**Purpose:** Search Reddit for streaming-related posts/comments, extract links, build graph nodes.

```python
def search_reddit(graph: GraphStore) -> dict:
    """
    Search Reddit via Apify for streaming mentions in sports subreddits.
    For each post/comment found:
      1. Create a reddit_account node for the author
      2. Extract invite links and domains from post text
      3. Create nodes and edges for each extracted item
      4. Save raw results to data/raw/reddit_raw.json

    Use config.REDDIT_SUBREDDITS as start URLs and config.REDDIT_SEARCH_TERMS
    as search terms.

    The Reddit Apify Actor (trudax/reddit-scraper) accepts input like:
    {
        "startUrls": [{"url": "https://www.reddit.com/r/soccer/"}],
        "searchTerms": ["free stream"],
        "maxItems": 50,
        "type": "posts"  # or "comments"
    }

    Field names to check in raw output:
      post["title"], post["body"] or post["selftext"],
      post["author"] or post["username"],
      post["url"], post["subreddit"]

    Same error handling as Twitter: never crash, log and continue.
    Returns summary stats dict.
    """
```

### 6.5 `collectors/apify_telegram.py` — Telegram Channel Scraping via Apify

**Purpose:** Scrape messages from public Telegram channels, extract links and domains.

```python
def scrape_telegram(graph: GraphStore) -> dict:
    """
    Scrape messages from public Telegram channels via Apify.
    For each channel in config.TELEGRAM_CHANNELS:
      1. Create a telegram_channel node
      2. Scrape recent messages
      3. Extract invite links and domains from message text
      4. Create nodes and edges

    The Telegram Apify Actor (danielmilevski9/telegram-channel-scraper)
    accepts input like:
    {
        "channelUsername": "sportsnews",
        "startMessageId": 1,
        "endMessageId": 100,
    }

    NOTE: Telegram channel scrapers vary in quality. Some require
    a range of message IDs (from-to), others accept a channel URL.
    Test the Actor manually on Apify's website first to understand
    its input format. If the Actor doesn't work, try alternatives:
      - "tri_angle/telegram-scraper"
      - "khadinakbar/telegram-channel-scraper"

    Field names to check in raw output:
      message["text"], message["date"],
      channel info may be in a separate object

    Save raw results to data/raw/telegram_raw.json.
    Same error handling: never crash.
    Returns summary stats dict.
    """
```

### 6.6 `collectors/certstream_monitor.py` — Live Certificate Transparency Monitor

**Purpose:** Connect to the global certificate transparency feed, score each new domain, flag suspicious ones, and push them to the graph + notify the frontend via WebSocket.

```python
import certstream
import asyncio
from rapidfuzz import fuzz
from graph_store import GraphStore
import config
from datetime import datetime

class CertstreamMonitor:
    def __init__(self, graph: GraphStore, notify_callback=None):
        """
        graph: the shared GraphStore instance
        notify_callback: async function to call when a domain is flagged.
            Signature: async notify_callback(domain_data: dict)
            This will push the alert to connected WebSocket clients.
        """
        self.graph = graph
        self.notify_callback = notify_callback
        self.running = False
        self.stats = {
            "certificates_seen": 0,
            "domains_scored": 0,
            "domains_flagged": 0,
        }

    def score_domain(self, domain: str) -> dict:
        """
        Score a domain name against piracy patterns.
        Returns:
        {
            "domain": "sportslive-free.xyz",
            "score": 8,
            "max_score": 15,  # theoretical max
            "reasons": [
                "keyword: stream (+3)",
                "keyword: live (+3)",
                "cheap TLD: .xyz (+2)",
            ],
            "flagged": True
        }

        Scoring rules (TIER 1 — fast local filter):
        1. For each keyword in config.CERT_KEYWORDS found in domain name:
           add CERT_SCORE_KEYWORD (but max 2 keyword bonuses to prevent
           inflation from domains like "livestreamfreesportshd.xyz")
        2. If TLD is in config.CERT_CHEAP_TLDS: add CERT_SCORE_CHEAP_TLD
        3. For each brand in config.CERT_KNOWN_BRANDS, compute
           rapidfuzz.fuzz.partial_ratio(brand, domain_without_tld).
           If any score > 70: add CERT_SCORE_BRAND_SIMILARITY
        4. If domain name (without TLD) is > 20 chars: add CERT_SCORE_LONG_DOMAIN
        5. If score >= CERT_TIER1_FLAG_THRESHOLD: pass to Tier 2 NLP queue

        IMPORTANT: Strip "www." and subdomains before scoring.
        Only score the registrable domain (e.g., "sportslive.xyz" not
        "cdn.sportslive.xyz").
        """

    def _on_cert_message(self, message, context):
        """
        Callback for certstream. Called for every new certificate.

        message["data"]["leaf_cert"]["all_domains"] contains a list of
        domain names the certificate covers.

        TWO-TIER ARCHITECTURE:
        For each domain:
          1. Skip if it's a known legitimate domain (google.com, etc.)
          2. Skip wildcard entries (*.example.com)
          3. Run Tier 1 scoring (fast, local, <1ms)
          4. If Tier 1 score >= CERT_TIER1_FLAG_THRESHOLD:
             → Put domain into tier2_queue (thread-safe queue.Queue)
             → Also put into notify_queue for frontend scrolling feed
          5. Tier 2 processing happens SEPARATELY in an async task
             (see DomainClassifierQueue.process_batch in nlp/domain_classifier.py)

        CRITICAL: This runs in a separate thread. Put items into
        queue.Queue objects ONLY. Never access GraphStore directly.
        Never make API calls here. Tier 1 is pure string operations.

        Also send ALL scored domains (even non-flagged) to a separate
        feed_queue so the frontend scrolling bar can show them passing by.
        Limit feed_queue to last 100 items to prevent memory growth.
        """

    async def enrich_domain(self, domain: str, node_id: str):
        """
        After a domain is flagged (by either Tier 1 or Tier 2), do
        background enrichment:
        1. DNS lookup (A record) via dnspython — get IP address
        2. Check if domain resolves (is it live?)
        3. Update the node's metadata with IP, is_live status

        This runs asynchronously and updates the graph after the fact.
        It's OK if enrichment fails — the node already exists with
        basic info from the certificate.

        Do NOT do HTTP requests to the domain — it might be malicious.
        DNS lookup only.
        """

    def start(self):
        """
        Start certstream listener in a background thread.
        Uses certstream.listen_for_events() which blocks,
        so it MUST run in a thread, not in the main asyncio loop.

        certstream.listen_for_events(
            self._on_cert_message,
            url="wss://certstream.calidog.io/"
        )
        """

    def stop(self):
        """Stop the listener."""

    def get_stats(self) -> dict:
        """Return current monitoring stats including Tier 1 and Tier 2 counts."""
```

**CRITICAL CERTSTREAM + NLP ARCHITECTURE:**

The two-tier system works like this:

```
Certstream WebSocket (~30 certs/sec)
    │
    ▼
TIER 1: Fast local scoring (Python thread, <1ms per domain)
    │ ── score < 3 → discard (shown in gray in feed bar)
    │ ── score >= 3 → pass to Tier 2 queue (~5% of domains)
    ▼
TIER 2: NLP batch classification (asyncio task, every 10 seconds)
    │ ── Drain up to 15 domains from queue
    │ ── Send batch to Claude Sonnet
    │ ── Claude analyzes: leetspeak, brand similarity, creative naming
    │ ── Returns: risk_level, decoded_name, reasons, confidence
    │
    ├── NLP says "not suspicious" → discard
    └── NLP says "suspicious" → add to graph + notify frontend
         │
         ▼
    Dashboard: node appears with pulse animation
    Side panel shows: Tier 1 score + Tier 2 NLP analysis
```

**Why two tiers?** Certstream pushes 30 domains/second. You can't send all of them to Claude — that's 180 API calls per minute, which would cost $50/hour and hit rate limits. Tier 1 filters locally in <1ms using simple string matching, cutting 95% of domains. Only the ~5% that look suspicious go to Tier 2 for deep NLP analysis. This means ~6 API calls per minute — cheap and fast.

**The demo payoff:** When a domain is flagged by Tier 2, the side panel shows BOTH analyses:
- "Tier 1 (instant): score 5/10 — keyword 'sport', cheap TLD .xyz"
- "Tier 2 (NLP): HIGH RISK, confidence 0.91 — leetspeak decoding: 'sp0rtz' = 'sports', similar to known brand 'sportsurge', likely streaming piracy"

Judges see a two-stage analysis pipeline. That's sophisticated. That's hackathon-winning.

**Thread safety notes:**

1. **certstream runs in its own thread.** It uses a blocking WebSocket loop internally. You MUST run it in a `threading.Thread(daemon=True)`. Do not try to integrate it into FastAPI's asyncio loop directly — it will block everything.

2. **Three queues bridge the thread boundary:**
   - `tier2_queue` (queue.Queue) — domains for NLP analysis
   - `notify_queue` (queue.Queue) — flagged domains for WebSocket push
   - `feed_queue` (queue.Queue, maxsize=100) — all scored domains for scrolling feed
   
   Certstream thread WRITES to these queues. FastAPI asyncio tasks READ from them.

3. **Notify the frontend.** Use FastAPI WebSockets:
   - Frontend opens a WebSocket to `ws://localhost:8000/ws/live`
   - Backend sends JSON messages:
     - `{"type": "feed_domain", "data": {"domain": "...", "tier1_score": 2, "flagged": false}}` — for scrolling feed
     - `{"type": "new_threat", "data": {full_node_dict}}` — for flagged domains (added to graph)
   - Frontend renders feed items in the bottom bar, adds flagged nodes to vis.js graph

4. **Don't score every subdomain.** Many certificates cover subdomains of the same registrable domain. Deduplicate: if you've already scored `sportslive.xyz` in the last 60 seconds, skip `www.sportslive.xyz` and `mail.sportslive.xyz`.

5. **Tier 1 performance.** At 30 certs/second, you'll process ~1,800 per minute. Tier 1 scoring must NOT do any I/O. Regex + string matching + one rapidfuzz call per known brand = ~0.5ms per domain. That's fine.

### 6.7 `scoring.py` — Threat Scoring, Clustering, and Lifecycle

**Purpose:** Analyze the graph to compute threat scores, detect operator clusters, and assign lifecycle stages.

```python
from graph_store import GraphStore
from rapidfuzz import fuzz
from datetime import datetime, timedelta
import config

def compute_threat_scores(graph: GraphStore) -> None:
    """
    For each node in the graph, compute a threat score (0-100) based on:
    1. Connection count: number of edges. Normalize across all nodes.
       More connections = higher threat.
    2. Recency: hours since last_seen. More recent = higher.
       Use exponential decay: recency_score = exp(-hours/48)
    3. Type weight: from config.THREAT_TYPE_WEIGHTS.
       Domains are more threatening than individual tweets.

    Final score = normalize_to_100(
        THREAT_WEIGHT_CONNECTIONS * connections_normalized +
        THREAT_WEIGHT_RECENCY * recency_score +
        THREAT_WEIGHT_TYPE * type_weight
    )

    Update each node's threat_score in-place. Save graph after.
    """

def detect_clusters(graph: GraphStore) -> None:
    """
    Detect operator clusters — groups of nodes likely run by the same
    entity based on shared infrastructure signals.

    Algorithm (simple, not Louvain — this is a hackathon):
    1. Get all domain nodes.
    2. For each pair of domains, compute a "same operator" score:
       - Same TLD? +1
       - Registered within CLUSTER_SAME_TLD_WINDOW_HOURS of each other? +2
       - Domain names are similar (rapidfuzz partial_ratio >
         CLUSTER_BRAND_SIMILARITY_THRESHOLD)? +2
       - Share a common neighbor (both linked to same Telegram channel
         or Twitter account)? +3
       - Same IP address? +3
    3. If same-operator score >= 4, merge them into a cluster.
    4. Use simple union-find to group transitive connections:
       if A clusters with B, and B clusters with C, then A-B-C are one cluster.
    5. Assign a cluster_id (e.g., "cluster_1", "cluster_2") to each
       node in the cluster. Also assign the cluster_id to all non-domain
       nodes connected to any node in the cluster.
    6. Add "same_operator" edges between all domain pairs in a cluster.

    Update nodes in-place. Save graph after.
    """

def assign_lifecycle_stages(graph: GraphStore) -> None:
    """
    For each domain node, assign a lifecycle stage based on its edges:

    - "setup": Domain node exists but has no edges to invite_links
      or social media accounts promoting it. Just registered.

    - "promotion": Domain has edges from social media accounts
      (twitter_account, reddit_account) or invite_links pointing to it,
      but fewer than 3 total promotion edges. Being promoted but not
      widely yet.

    - "active": Domain has 3+ promotion edges OR has edges from
      multiple source types (e.g., both Twitter AND Telegram).
      Actively being distributed.

    - "dormant": Domain's last_seen is more than 48 hours ago AND
      it was previously in "active" or "promotion" stage.
      The operation has moved on.

    Update lifecycle_stage in-place. Save graph after.
    """

def compute_velocity(graph: GraphStore, node_id: str,
                      window_hours: int = 24) -> float:
    """
    Compute how much new activity a node has generated recently.
    Count edges added in the last window_hours.
    Return edges_per_hour as a float.

    This is displayed in the side panel as "activity velocity"
    to show judges which nodes are hot right now.
    """

def run_all_analysis(graph: GraphStore) -> None:
    """
    Run all analysis in order:
    1. compute_threat_scores
    2. detect_clusters
    3. assign_lifecycle_stages
    Log timing for each step.
    """
```

### 6.8 `scripts/generate_synthetic.py` — Realistic Demo Data

**Purpose:** Create 80-100 nodes that tell a coherent piracy story with 3 operator clusters.

```python
from graph_store import GraphStore
from datetime import datetime, timedelta
import random
import uuid

def generate_synthetic_data(graph: GraphStore) -> None:
    """
    Generate three operator clusters + scattered independent nodes.
    All synthetic data should look realistic — no "test123" names.

    CLUSTER 1 — "The Streameast Network" (~20 nodes):
    A professional piracy operation using multiple mirror domains.
    - 4 domain nodes:
      "streameast-hd.xyz", "streameast-live.top",
      "sportshd-free.online", "streameast-v2.site"
      All registered within 48 hours of each other.
      All have metadata: registrar="NameCheap", cert_issuer="Let's Encrypt"
      All resolve to similar IP ranges (synthetic: "104.21.xx.xx")
    - 3 telegram_channel nodes:
      "@streameast_official", "@sportsHD_links", "@freefootball_live"
    - 5 twitter_account nodes:
      "@streamking2024" (followers: 12400),
      "@hdmatches_free" (followers: 8200),
      "@livesports_247" (followers: 5600),
      "@footystreams99" (followers: 3100),
      "@sportslinkbot" (followers: 15800)
    - 3 invite_link nodes:
      "https://t.me/streameast_official"
      "https://discord.gg/fakeABC123"
      "https://t.me/sportsHD_links"
    - 4 reddit_account nodes:
      "u/streamguy99", "u/matchday_links", "u/footballfree_hd", "u/sportshd_bot"

    Edges (these tell the story):
      - Each Twitter account "posted" 1-2 invite links
      - Each invite link "links_to" a Telegram channel
      - Each Telegram channel "promotes" 1-2 domains
      - Twitter accounts "promotes" domains directly too
      - Reddit accounts "posted" invite links
      - All 4 domains get "same_operator" edges between each pair
      - Domains "resolves_to" IP address node if desired (optional)

    Timestamps: stagger over the last 72 hours to show a realistic
    buildup. Oldest domain registered 72h ago, newest 12h ago.
    Social media posts start appearing 48h ago, peak 24h ago.

    CLUSTER 2 — "The Telegram Ring" (~15 nodes):
    A network of Telegram channels that cross-promote each other.
    - 2 domain nodes:
      "livematch-hd.site", "soccerstreams-today.online"
    - 6 telegram_channel nodes that cross-post links
    - 4 twitter_account nodes
    - 3 invite_link nodes

    Key feature: channels have "cross_posts" edges between them,
    showing coordinated sharing. This cluster looks different from
    Cluster 1 — it's Telegram-centric rather than domain-centric.

    CLUSTER 3 — "The Lone Wolf" (~8 nodes):
    A single high-follower Twitter account that creates new domains
    every few days.
    - 1 twitter_account: "@megastreams_io" (followers: 42000)
    - 4 domain nodes registered over the last 2 weeks:
      "megastreams.xyz" (dormant — last_seen 12 days ago)
      "megastreams-v2.top" (dormant — last_seen 8 days ago)
      "megastreams-hd.live" (dormant — last_seen 3 days ago)
      "megastreams-new.site" (active — last_seen 2 hours ago)
    - 2 invite_link nodes
    - 1 telegram_channel

    Key feature: this cluster shows the MIGRATION pattern.
    Domains go dormant one by one as new ones activate.
    Judges can see the lifecycle: setup → promotion → active → dormant.

    SCATTERED INDEPENDENTS (~15 nodes):
    - 5 twitter_account nodes with no cluster affiliation, each having
      posted 1 invite link or promoted 1 domain. Low followers (100-500).
    - 4 domain nodes flagged by certstream with no known connections yet.
      lifecycle_stage="setup".
    - 3 invite_link nodes from Reddit posts with no connected domain.
    - 3 reddit_account nodes with minimal connections.

    These make the graph look realistic — not everything is neatly
    clustered in real piracy intelligence either.

    AFTER generating all nodes and edges:
    - Call scoring.run_all_analysis(graph) to compute threat scores,
      detect clusters, and assign lifecycle stages.
    - Save graph.
    """
```

**Critical: Make the names look real.** Judges will immediately notice lazy names like "test_domain_1" or "user_abc". Use names that look like actual piracy operations — because that's exactly what real piracy domains look like. The names above are realistic examples.

### 6.9 `scripts/collect_data.py` — Pre-Demo Data Collection

```python
"""
Run this 1-2 hours before the demo to collect real data from Apify.
Usage: python scripts/collect_data.py

Flow:
1. Load existing graph (which may already have synthetic data)
2. Run apify_twitter.search_twitter(graph)  — uses NLP if available, regex fallback
3. Run apify_reddit.search_reddit(graph)    — uses NLP if available, regex fallback
4. Run apify_telegram.scrape_telegram(graph) — uses NLP if available, regex fallback
5. Print NLP summary: how many posts classified, how many flagged, intent breakdown
6. Run scoring.run_all_analysis(graph)
7. Print overall summary stats
8. Save graph

If Apify token is not configured, all collectors return empty results.
If Anthropic API key is not configured, NLP is skipped and regex is used.
The synthetic data carries the demo either way.
"""
```

### 6.12 `app.py` — FastAPI Server

```python
"""
FastAPI server with:
- Static file serving (index.html)
- REST API for graph data
- WebSocket for live certstream alerts + feed
- Background thread for certstream Tier 1
- Background asyncio task for certstream Tier 2 NLP batching
"""

# Endpoints:

GET  /                          → serve static/index.html
GET  /api/graph                 → return full graph (nodes + edges) as JSON
GET  /api/stats                 → return graph stats (node counts, cluster counts, NLP stats)
GET  /api/node/{node_id}        → return single node with all its edges and neighbors
GET  /api/cluster/{cluster_id}  → return all nodes and edges in a cluster
GET  /api/certstream/stats      → return certstream monitoring stats (Tier 1 + Tier 2)
POST /api/reset                 → clear graph, regenerate synthetic data
POST /api/collect               → trigger Apify collection + NLP pipeline (for testing, not demo)
WS   /ws/live                   → WebSocket for real-time certstream alerts + feed

# Implementation details:

# On startup:
#   1. Load graph from data/graph.json
#   2. If graph is empty, run generate_synthetic.py automatically
#   3. Start certstream monitor in background daemon thread (Tier 1)
#   4. Start asyncio task: poll certstream notify_queue every 0.5s,
#      push to all connected WebSocket clients
#   5. Start asyncio task: poll certstream feed_queue every 0.3s,
#      push feed items to WebSocket clients (scrolling bar)
#   6. Start asyncio task: run Tier 2 NLP batch processing every
#      CERT_TIER2_BATCH_INTERVAL seconds (drain tier2_queue, call
#      DomainClassifierQueue.process_batch, push results to graph + WebSocket)

# Background certstream flow:
#   certstream thread (Tier 1)
#     → scores domains locally (<1ms)
#     → puts ALL scored domains in feed_queue (for scrolling bar)
#     → puts suspicious domains (score >= threshold) in tier2_queue
#
#   asyncio task (every 0.3s) → reads feed_queue → pushes to WebSocket
#   asyncio task (every 0.5s) → reads notify_queue → pushes flagged to WebSocket
#   asyncio task (every 10s)  → reads tier2_queue → NLP batch → graph + WebSocket

# WebSocket message types from server to client:
#   {"type": "feed_domain", "data": {"domain":"...", "tier1_score":2, "flagged":false}}
#   {"type": "new_threat", "data": {full_node_dict_with_nlp_metadata}}
#   {"type": "stats_update", "data": {stats_dict}}

# CORS: allow all origins
# Error handling: every endpoint wrapped in try/except, returns JSON error

# IMPORTANT: The certstream background thread must be daemon=True
# so it dies when the main process exits.
```

# Background certstream flow:
#   certstream thread → puts flagged domains in queue.Queue()
#   asyncio task (every 0.5s) → reads from queue → adds to graph →
#     pushes to WebSocket clients → runs quick enrichment

# WebSocket messages from server to client:
#   {"type": "new_domain", "data": {node_dict}}
#   {"type": "stats_update", "data": {stats_dict}}

# CORS: allow all origins
# Error handling: every endpoint wrapped in try/except, returns JSON error

# IMPORTANT: The certstream background thread must be daemon=True
# so it dies when the main process exits. Don't let it keep the
# server alive after Ctrl+C.
```

### 6.11 `static/index.html` — The Dashboard

This is the single most important file. If the dashboard looks bad, nothing else matters. If it looks amazing, judges will forgive any backend shortcuts.

**Design Direction:** Dark, command-center aesthetic. Think cybersecurity operations center. Dark background (#0a0a0f), neon accent colors for node types, subtle grid pattern background, monospace font for numbers and stats, smooth animations.

**Layout (single page, no scrolling):**

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER BAR                                                          │
│  "Digital Asset Protection — Threat Intelligence"                    │
│  Stats: 142 entities | 3 networks | 12 flagged today | ● LIVE       │
├────────────────────────────────────┬─────────────────────────────────┤
│                                    │  SIDE PANEL (hidden by default) │
│                                    │                                 │
│         MAIN GRAPH AREA            │  Shows when a node is clicked:  │
│         (vis.js network)           │  - Node name + type icon        │
│                                    │  - Threat score (big number)    │
│         Full width when panel      │  - Lifecycle stage (colored)    │
│         is hidden, shrinks         │  - First seen / Last seen       │
│         when panel opens           │  - Metadata (followers, TLD..)  │
│                                    │  - Connections list             │
│                                    │  - Activity timeline            │
│                                    │  - Cluster membership           │
├────────────────────────────────────┼─────────────────────────────────┤
│  LIVE FEED BAR (bottom, ~100px)                                      │
│  Scrolling certstream domains: "sportslive.xyz ● score:8 ●2s ago"   │
│  Flagged domains pulse red. Non-flagged scroll by in gray.           │
└──────────────────────────────────────────────────────────────────────┘
```

**vis.js Graph Configuration:**

```javascript
// Node colors by type
const NODE_COLORS = {
    domain:           { background: "#ef4444", border: "#dc2626" },  // red
    twitter_account:  { background: "#3b82f6", border: "#2563eb" },  // blue
    telegram_channel: { background: "#22c55e", border: "#16a34a" },  // green
    reddit_account:   { background: "#f97316", border: "#ea580c" },  // orange
    invite_link:      { background: "#a855f7", border: "#9333ea" },  // purple
    torrent:          { background: "#eab308", border: "#ca8a04" },  // yellow
    ip_address:       { background: "#6b7280", border: "#4b5563" },  // gray
};

// Node shapes by type
const NODE_SHAPES = {
    domain:           "diamond",
    twitter_account:  "dot",
    telegram_channel: "triangle",
    reddit_account:   "square",
    invite_link:      "star",
    torrent:          "hexagon",
    ip_address:       "box",
};

// Node size scales with threat_score
// size = 10 + (threat_score / 100) * 30  →  range: 10 to 40

// Physics settings (TUNE THESE for visual clarity):
const options = {
    physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
            gravitationalConstant: -30,
            centralGravity: 0.005,
            springLength: 120,
            springConstant: 0.05,
            damping: 0.4,
        },
        stabilization: {
            iterations: 200,        // settle quickly on load
            updateInterval: 25,
        },
    },
    interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
    },
    edges: {
        color: { color: "#374151", highlight: "#60a5fa", opacity: 0.6 },
        width: 1,
        smooth: { type: "curvedCW", roundness: 0.15 },
    },
};
```

**Features to implement in the HTML/JS:**

1. **Graph rendering:** Fetch `/api/graph` on page load, build vis.js DataSets, render.

2. **Click handler:** When a node is clicked, fetch `/api/node/{id}`, populate side panel with details, highlight connected edges.

3. **Cluster highlighting:** When side panel shows a clustered node, add a "Show Cluster" button. Clicking it highlights all nodes in that cluster (change border to white, increase border width).

4. **Live feed bar:** Open WebSocket to `/ws/live`. Handle two message types:
   - `feed_domain`: Add a line to the scrolling feed bar at bottom (gray for benign, yellow for Tier 1 flagged)
   - `new_threat`: Domain confirmed by Tier 2 NLP — show in red with a pulse, add node to vis.js graph with scale-in animation

5. **Stats bar:** Fetch `/api/stats` on load and every 30 seconds. Update the header numbers. Include NLP stats: "NLP: 47 posts classified | 12 flagged"

6. **Pulse animation for new nodes:** When a node is added live (from certstream Tier 2), set its initial size to 0, then animate to full size over 0.5s using vis.js's `nodes.update()` with a setTimeout chain.

7. **NLP insight display in side panel:** When a node has NLP metadata, show it prominently:
   - **For posts:** "🤖 NLP Analysis: intent=coded_distribution, confidence=92%, signals: [DM-based distribution, coded language]"
   - **For domains:** "🤖 Tier 2 Analysis: decoded='stream east HD', risk=HIGH, brand match: streameast (confidence: 91%)"
   - Show the NLP summary as a highlighted quote in the side panel
   - Use a small "AI" badge icon next to NLP-analyzed nodes in the graph

8. **Regex vs NLP comparison view (optional but impressive):** Add a small toggle in the side panel that shows "What regex found" vs "What NLP found" for the same post. This is the killer demo moment — show a post like "DM me for tonight's match" where regex found NOTHING but NLP flagged it as coded distribution.

9. **Responsive:** Must look good on a 1080p projector. Test at 1920x1080.

**Font choices:**
- Headers: `"JetBrains Mono", "Fira Code", monospace` — techy feel
- Body text: `"IBM Plex Sans", sans-serif` — clean readability
- Numbers/stats: `"JetBrains Mono", monospace` — always monospace for data
- Load both from Google Fonts CDN

**Color palette (CSS variables):**
```css
:root {
    --bg-primary: #0a0a0f;        /* near-black */
    --bg-secondary: #111118;      /* cards, panels */
    --bg-tertiary: #1a1a24;       /* hover states */
    --text-primary: #e2e8f0;      /* main text */
    --text-secondary: #94a3b8;    /* labels, secondary */
    --accent-red: #ef4444;        /* domains, alerts */
    --accent-blue: #3b82f6;       /* Twitter, info */
    --accent-green: #22c55e;      /* Telegram, success */
    --accent-orange: #f97316;     /* Reddit, warnings */
    --accent-purple: #a855f7;     /* invite links */
    --accent-yellow: #eab308;     /* torrents */
    --border-color: #1e293b;      /* subtle borders */
    --glow-red: 0 0 20px rgba(239, 68, 68, 0.3);
    --glow-blue: 0 0 20px rgba(59, 130, 246, 0.3);
    --glow-green: 0 0 20px rgba(34, 197, 94, 0.3);
}
```

**Background effect:** Subtle CSS grid pattern on the main background:
```css
body {
    background-color: var(--bg-primary);
    background-image:
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 40px 40px;
}
```

**Live indicator:** A pulsing green dot in the header with "LIVE" text, indicating certstream is running. CSS animation:
```css
@keyframes pulse-live {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.live-dot {
    width: 8px; height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse-live 2s ease-in-out infinite;
    display: inline-block;
}
```

---

## 7. `requirements.txt`

```
fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9
apify-client>=1.6
anthropic>=0.39
certstream>=1.12
rapidfuzz>=3.6
dnspython>=2.5
websockets>=12.0
```

---

## 8. README.md Content

Include:

1. **What this is** — one paragraph: piracy threat intelligence dashboard with NLP-powered classification
2. **Prerequisites:**
   - Python 3.10+
   - Apify account (free, apify.com, no credit card) — get API token from Settings → Integrations
   - Anthropic API key — for NLP pipeline (Claude Sonnet). Get from console.anthropic.com. Total cost for demo: ~$1-2.
   - Internet connection (for Apify API + Anthropic API + certstream WebSocket)
3. **Setup:**
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Configure:** Edit `config.py`:
   - Paste your Apify API token in `APIFY_API_TOKEN`
   - Paste your Anthropic API key in `ANTHROPIC_API_KEY`
   - Set `NLP_ENABLED = False` if you want regex-only mode (no API cost)
5. **Prepare demo data:**
   ```
   python scripts/generate_synthetic.py    # creates synthetic graph
   python scripts/collect_data.py          # adds real Apify data + NLP analysis (optional)
   ```
6. **Run:**
   ```
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```
   Open http://localhost:8000
7. **Demo flow:** what to click, what to say
8. **Troubleshooting:**
   - "Apify Actor failed" → try a different Actor ID in config.py
   - "NLP classification failed" → check ANTHROPIC_API_KEY, or set NLP_ENABLED=False for regex fallback
   - "Certstream disconnected" → it reconnects automatically, wait 5s
   - "Graph looks cluttered" → adjust physics constants in index.html
   - "No domains flagged by certstream" → lower CERT_TIER1_FLAG_THRESHOLD in config.py
   - "Tier 2 NLP not firing" → check that certstream Tier 1 is passing domains (lower threshold)

---

## 9. Critical Implementation Rules for Claude Code

1. **The dashboard IS the project.** If you run out of time, skip Apify collectors entirely. The synthetic data + certstream + a beautiful graph visualization is a complete demo. A gorgeous frontend with mock data beats an ugly frontend with real data every time at a hackathon.

2. **Never crash the server.** Every endpoint, every WebSocket handler, every background task, every NLP API call wraps its work in try/except. Log errors to console but keep running. A crash during a live demo is unrecoverable.

3. **Never block the event loop.** Certstream runs in a daemon thread. Apify calls (in collect_data.py) are blocking but they run as a separate script, not in the server. NLP Tier 2 batch calls run in the asyncio loop but they're non-blocking (anthropic client supports async). DNS lookups in enrichment use asyncio-compatible dnspython methods.

4. **Certstream thread safety.** Use THREE `queue.Queue()` objects as the bridge between the certstream thread and the FastAPI asyncio loop: feed_queue (all domains), tier2_queue (suspicious domains for NLP), notify_queue (confirmed threats for graph). NEVER access the GraphStore from the certstream thread directly.

5. **NLP is always optional.** Every code path that calls the NLP pipeline MUST have a fallback. If `config.NLP_ENABLED` is False, or `config.ANTHROPIC_API_KEY` is empty, or the API call fails, the system falls back to regex extraction silently. The demo MUST work without NLP — NLP makes it better, not possible.

6. **NLP error handling is triple-layered.** (a) Check config before calling. (b) Wrap API call in try/except. (c) Validate JSON response before using it. Any failure at any layer → return empty results → caller falls back to regex. Log the error but NEVER crash.

7. **NLP responses can be malformed.** Claude sometimes returns markdown-fenced JSON (```json ... ```), sometimes includes preamble text before the JSON, sometimes returns objects instead of arrays. The parser MUST handle all of these: strip fences, strip preamble, try parsing, validate structure. If the response is truly unparseable, log it and return empty.

8. **Graph deduplication is critical.** When the same Twitter handle appears in both synthetic data and real Apify data, merge don't duplicate. The `add_node` function MUST check for existing (type, label) matches and merge metadata if found.

9. **vis.js performance.** With 100+ nodes, vis.js can lag if you're not careful:
   - Set `stabilization.iterations: 200` (not 1000)
   - Use `barnesHut` or `forceAtlas2Based` solver (not `repulsion`, which is O(n²))
   - Set `physics.enabled: false` after initial stabilization if needed
   - Don't use shadow rendering on nodes (expensive)

7. **WebSocket reliability.** The frontend WebSocket connection will drop occasionally (browser tab sleeps, network hiccup). Implement auto-reconnect in the JS:
   ```javascript
   function connectWebSocket() {
       const ws = new WebSocket("ws://localhost:8000/ws/live");
       ws.onclose = () => setTimeout(connectWebSocket, 2000);
       ws.onmessage = (event) => { /* handle */ };
   }
   ```

8. **Test certstream early.** It's the component most likely to have issues:
   - Corporate/university firewalls may block WebSocket connections
   - The certstream server (certstream.calidog.io) occasionally goes down
   - If certstream doesn't work on the demo network, have a fallback: a Python script that simulates certstream by generating fake domain alerts every 3 seconds. Name it `collectors/fake_certstream.py` and switch to it in app.py if needed.

9. **Don't over-engineer the Apify collectors.** The field names in Apify responses vary by Actor and can change without notice. After your FIRST successful run, inspect `data/raw/*.json` files and hardcode the correct field paths. Don't build a generic parser that handles every possible Actor — build one that handles YOUR specific Actor.

10. **All times in UTC.** Use `datetime.utcnow().isoformat()` everywhere. Don't mix timezones.

---

## 10. Certstream Fallback Script

If certstream.calidog.io is down or blocked on the demo network, use this fake certstream that generates realistic-looking domain alerts:

```python
# collectors/fake_certstream.py
"""
Simulates certstream by generating fake domain alerts every 2-5 seconds.
Use this if real certstream is blocked on the demo network.

Generates domains that mix:
- Genuinely suspicious names (high score, will be flagged)
- Benign names (low score, will scroll by unflagged)

Ratio: ~1 flagged domain per 8-10 benign ones.
"""

import random
import time
import threading
from queue import Queue

SUSPICIOUS_TEMPLATES = [
    "stream{sport}-{adj}.{tld}",
    "{sport}live-{adj}.{tld}",
    "free{sport}hd.{tld}",
    "watch{sport}-{adj}.{tld}",
    "{brand}-{suffix}.{tld}",
]

BENIGN_DOMAINS = [
    "myshop-store.com", "blog-portfolio.dev", "acme-solutions.io",
    "photography-studio.net", "recipe-tracker.app", "api-gateway.cloud",
    # ... add 30+ more realistic boring domains
]

SPORTS = ["football", "soccer", "match", "sports", "nba", "ufc"]
ADJS = ["free", "hd", "live", "today", "new", "v2", "pro"]
TLDS = [".xyz", ".top", ".site", ".online", ".live"]
BRANDS = ["streameast", "sportsurge", "crackstream", "buffstream"]
SUFFIXES = ["hd", "v2", "new", "live", "pro", "today"]

def generate_suspicious_domain() -> str:
    """Generate a domain that WILL score high enough to flag."""

def generate_benign_domain() -> str:
    """Return a random boring domain."""

def run_fake_certstream(output_queue: Queue, interval_range=(1, 4)):
    """
    Continuously generate fake certificate events.
    Every interval_range seconds, generate 1-3 domains.
    ~10% chance of a suspicious domain, ~90% benign.
    Put results in output_queue in the same format as real certstream.
    """
```

In `app.py`, add a config toggle:
```python
USE_FAKE_CERTSTREAM = False  # Set True if real certstream is blocked
```

---

## 11. Testing Checklist (Before Demo)

- [ ] Server starts without errors: `uvicorn app:app`
- [ ] Dashboard loads at http://localhost:8000 with graph visible
- [ ] Graph has 80+ nodes in 3 visible clusters + scattered independents
- [ ] Clicking a node opens side panel with correct details
- [ ] Side panel shows threat score, lifecycle stage, connections
- [ ] Nodes with NLP metadata show the AI analysis badge + NLP insights in side panel
- [ ] "Show Cluster" button highlights all nodes in a cluster
- [ ] Certstream live feed scrolls at bottom of dashboard (benign in gray, Tier 1 flagged in yellow)
- [ ] Tier 2 NLP processes batches every ~10 seconds (check server console logs)
- [ ] At least 1 domain is confirmed by Tier 2 NLP within 5 minutes of watching
- [ ] NLP-confirmed domain appears on graph in red with pulse animation
- [ ] Side panel for NLP-confirmed domain shows BOTH Tier 1 score AND Tier 2 NLP analysis
- [ ] Stats bar shows accurate counts including NLP stats
- [ ] WebSocket auto-reconnects if you refresh the page
- [ ] `/api/reset` clears and regenerates the graph
- [ ] Graph doesn't lag or freeze with 100+ nodes
- [ ] Dashboard looks good on 1920x1080 (projector resolution)
- [ ] Dark theme is readable from 3 meters away (stage distance)
- [ ] Setting NLP_ENABLED=False: system still works on regex fallback
- [ ] Setting ANTHROPIC_API_KEY="": NLP degrades gracefully, no crash
- [ ] If certstream fails, fake_certstream works as backup
- [ ] No console errors in browser DevTools

---

## 12. What NOT to Build

Explicitly skip these:

- **Neo4j** — in-memory Python dict is fine for 100 nodes
- **PostgreSQL** — JSON file is fine
- **Redis/Celery** — no task queues needed
- **Actual web crawling (Component 1)** — mock data
- **DHT protocol (Component 4)** — mock data
- **User auth/sessions** — zero auth
- **WHOIS lookups** — unreliable and slow, skip for demo
- **HTTP requests to flagged domains** — potentially dangerous, DNS only
- **Louvain/PageRank algorithms** — simple heuristic clustering is fine
- **Multiple pages** — single page dashboard only
- **Mobile responsiveness** — 1080p desktop only
- **Docker** — run directly on Windows
- **Tests** — manual testing against checklist

Everything above goes in the "production roadmap" slide.

---

## 13. Suggested Demo Script (2.5 minutes)

**0:00–0:15** "We don't just detect pirated content — we find the networks behind it. Our system uses AI to monitor Twitter, Reddit, Telegram, and new domain registrations, mapping organized piracy operations automatically."

**0:15–0:45** Dashboard is showing. "In the last 24 hours, our system identified 3 organized piracy operations." Click on the biggest cluster. Side panel opens. "These four domains were registered by the same operator within 48 hours — same registrar, same IP range. They're promoted by 5 Twitter accounts and 3 Telegram channels. One takedown request shuts down the entire operation."

**0:45–1:05** Click on a Twitter account node that has NLP metadata. "Here's where it gets interesting. This account never posted a single URL. Most detection systems would miss it completely." Point at the NLP analysis in the side panel. "Our AI pipeline flagged it anyway — it classified the language as 'coded distribution' with 92% confidence. The tweet said 'DM me for tonight's match.' No link, no domain — just coded language that our NLP caught."

**1:05–1:25** Click on The Lone Wolf cluster. "This is a repeat offender. One account, 42,000 followers. Every time a domain goes dark—" point at the dormant nodes "—they spin up a new one. Our system tracks the migration pattern and predicts when the next domain will appear."

**1:25–1:45** Point at the live feed bar at the bottom. "This is happening right now. Every new SSL certificate worldwide passes through our two-stage scanner." Wait for a domain to appear (or point at one already flagged). "Stage one filters locally in under a millisecond. Stage two sends suspicious candidates to our AI for deep analysis — it decodes leetspeak, matches brand variations, and catches creative evasion. That domain was just registered and analyzed in real time."

**1:45–2:05** Zoom out to full graph. "Individual links are noise. The network is the signal. We're not playing whack-a-mole with domains — we're mapping operations."

**2:05–2:20** "Combined with Module 1's fingerprinting engine, we can detect unauthorized content AND trace it back to the source. Content detection plus AI-powered threat intelligence — that's the full picture."

---

## 14. How Module 2 Connects to Module 1

You do NOT need to build this integration. Just mention it verbally during the demo.

The conceptual link: when Module 1's fingerprinting system detects a pirated clip, it could report the source URL/domain to Module 2's graph. That domain becomes a node, the system traces its operator network, and enforcement targets the operator — not just the individual link.

If judges ask "are these connected?": "Yes — Module 1 feeds detection events into Module 2's graph. A flagged video on streameast-hd.xyz would automatically create a node here, and we'd see it's part of this 4-domain cluster. One enforcement action covers all four sites."

---

## 15. Final Notes for Claude Code

Build in the order specified in section 5. The dashboard (Checkpoint 1) comes FIRST, before any backend work. A beautiful empty graph is a better starting point than a complete backend with no frontend.

**Priority order if running out of time:**
1. Dashboard with synthetic data (Checkpoints 1-2) — MINIMUM viable demo
2. Apify + regex extraction (Checkpoint 3) — adds real data
3. NLP pipeline (Checkpoint 4) — THE differentiator, the thing judges remember
4. Certstream with Tier 1 + Tier 2 (Checkpoint 5) — the live "wow" moment
5. Polish (Checkpoint 6) — makes everything look professional

The NLP pipeline (Checkpoint 4) is the hackathon-winning feature, but it requires Checkpoints 1-3 working first. Build the regex fallback path first, verify it works, THEN layer NLP on top. Never start with NLP — you need the fallback path as insurance.

The certstream integration (Checkpoint 5) is the riskiest component. Build it after NLP so you always have a working fallback (synthetic data + NLP-classified real data). If certstream doesn't work on the demo network, switch to fake_certstream and nobody will know the difference — the UX is identical.

The Apify integration (Checkpoint 3) is important for real data but the system must work without it. If the token isn't configured or an Actor fails, the system must work perfectly on synthetic data alone.

Spend disproportionate time on the vis.js graph aesthetics. The graph IS the demo. Node colors, sizes, edge curvature, hover effects, click animations, cluster highlighting, NLP insight badges — these visual details are what judges remember. A well-tuned graph with 80 synthetic nodes is more impressive than a messy graph with 200 real nodes.

**The NLP demo moment matters most.** When you click a node and the side panel shows "NLP classified this as coded distribution with 92% confidence — detected patterns: DM-based distribution, coded language" — that's the moment judges understand this isn't just another web scraper. Invest in making that side panel beautiful and informative.

Test on the actual demo laptop. Test on the actual demo network (for certstream + API calls). Test with the actual projector resolution. Test 30 minutes before going on stage.

Good luck. Build the dashboard first. Layer intelligence on top. Demo boldly.
