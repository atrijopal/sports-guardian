# config.py

# ---- Apify ----
APIFY_API_TOKEN = ""

APIFY_TWITTER_ACTOR = "apidojo/tweet-scraper"
APIFY_REDDIT_ACTOR = "trudax/reddit-scraper"
APIFY_TELEGRAM_ACTOR = "danielmilevski9/telegram-channel-scraper"

TWITTER_QUERIES = [
    "football stream t.me/",
    "soccer live stream discord.gg/",
    "match free stream link",
    "sports stream telegram",
    "football live free HD",
]
TWITTER_MAX_ITEMS_PER_QUERY = 30

REDDIT_SUBREDDITS = [
    "https://www.reddit.com/r/soccer/",
    "https://www.reddit.com/r/sports/",
    "https://www.reddit.com/r/football/",
]
REDDIT_SEARCH_TERMS = ["free stream", "live stream link", "watch free"]
REDDIT_MAX_ITEMS = 50

TELEGRAM_CHANNELS = ["@sportsnews", "@footballupdates"]
TELEGRAM_MAX_MESSAGES = 100

# ---- Certstream Domain Scoring (Tier 1) ----
CERT_KEYWORDS = ["stream", "sport", "live", "hd", "free", "match",
                 "watch", "football", "soccer", "cricket", "nba",
                 "ufc", "boxing", "fpl"]
CERT_CHEAP_TLDS = [".xyz", ".top", ".site", ".online", ".live",
                   ".stream", ".club", ".fun", ".icu", ".buzz"]
CERT_KNOWN_BRANDS = ["streameast", "sportsurge", "crackstream",
                     "buffstream", "720pstream", "markkystream",
                     "methstream", "weakspell", "sportshd"]
CERT_SCORE_KEYWORD          = 3
CERT_SCORE_CHEAP_TLD        = 2
CERT_SCORE_BRAND_SIMILARITY = 4
CERT_SCORE_LONG_DOMAIN      = 1
CERT_TIER1_FLAG_THRESHOLD   = 3
CERT_TIER2_BATCH_INTERVAL   = 10
CERT_TIER2_MAX_BATCH        = 15

# ---- Google APIs ----
GEMINI_API_KEY        = "YOUR_GEMINI_API_KEY_HERE"
YOUTUBE_API_KEY       = "YOUR_YOUTUBE_API_KEY_HERE"
SAFE_BROWSING_API_KEY = "YOUR_SAFE_BROWSING_API_KEY_HERE"

GEMINI_MODEL     = "gemini-2.0-flash"
NLP_MODEL        = "gemini-2.0-flash"
NLP_MAX_TOKENS   = 1500
NLP_BATCH_SIZE   = 15
NLP_ENABLED      = True
NLP_TEMPERATURE  = 0.0
SAFE_BROWSING_ENABLED = True

# ---- Background Task Intervals (seconds) ----
SB_SWEEP_INTERVAL      = 300    # Safe Browsing full sweep every 5 min
AI_BRIEFING_INTERVAL   = 1800   # Gemini briefing regeneration every 30 min
YT_HUNT_INTERVAL       = 900    # YouTube piracy hunt every 15 min

# ---- YouTube Hunt Queries ----
YOUTUBE_HUNT_QUERIES = [
    "football live stream free 2025",
    "cricket live stream free HD",
    "NBA live stream free watch",
    "Champions League live stream free",
    "IPL live stream free 2025",
]
YOUTUBE_MAX_HUNT_RESULTS = 5

# ---- Threat Scoring ----
THREAT_WEIGHT_CONNECTIONS = 0.4
THREAT_WEIGHT_RECENCY     = 0.3
THREAT_WEIGHT_TYPE        = 0.3
THREAT_TYPE_WEIGHTS = {
    "domain":           1.0,
    "youtube_channel":  0.9,
    "telegram_channel": 0.8,
    "twitter_account":  0.6,
    "reddit_account":   0.5,
    "invite_link":      0.7,
    "torrent":          0.6,
    "ip_address":       0.4,
}

# ---- Clustering ----
CLUSTER_SAME_TLD_WINDOW_HOURS       = 72
CLUSTER_SHARED_CHANNEL_THRESHOLD    = 2
CLUSTER_BRAND_SIMILARITY_THRESHOLD  = 75

# ---- Lifecycle ----
LIFECYCLE_STAGES = {
    "setup":     {"color": "#6b7280", "label": "Setup"},
    "promotion": {"color": "#f59e0b", "label": "Promotion"},
    "active":    {"color": "#ef4444", "label": "Active"},
    "dormant":   {"color": "#374151", "label": "Dormant"},
}

# ---- Paths ----
GRAPH_DATA_PATH = "data/graph.json"
RAW_DATA_DIR    = "data/raw"

# ---- Server ----
HOST = "0.0.0.0"
PORT = 8002
