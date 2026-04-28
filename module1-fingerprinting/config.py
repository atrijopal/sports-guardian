# config.py — All tunable parameters in one place. Tune here, not in layer files.

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

# ---- Google APIs ----
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
GEMINI_MODEL = "gemini-2.0-flash"

YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY_HERE"
YOUTUBE_SEARCH_ENABLED = True
YOUTUBE_MAX_RESULTS = 5
