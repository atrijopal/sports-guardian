# config.py

# ---- Secret Keys ----
WATERMARK_SECRET_KEY = "hackathon-demo-secret-key-2024"
WATERMARK_SALT = "sports-asset-protection-v1"

# ---- Session ID ----
SESSION_ID_BITS = 64
SESSION_ID_BYTES = 8

# ---- Reed-Solomon Error Correction ----
RS_ERROR_CORRECTION_SYMBOLS = 10

# ---- Layer 1: Spread Spectrum Visual ----
L1_FRAME_INTERVAL = 5
L1_BLOCK_SIZE = 32
L1_NOISE_STRENGTH = 4.0
L1_CORRELATION_THRESHOLD = 0.08
L1_MIN_FRAME_AGREEMENT = 0.45

# ---- Layer 2: Audio BPSK ----
L2_CARRIER_FREQ = 19000
L2_BIT_DURATION_MS = 50
L2_AMPLITUDE = 0.008
L2_REPEAT_INTERVAL_SEC = 10
L2_SAMPLE_RATE = 44100
L2_PHASE_DETECTION_THRESHOLD = 0.2
L2_BANDPASS_LOW = 18000
L2_BANDPASS_HIGH = 20500

# ---- Layer 3: DCT Structural ----
L3_DCT_BLOCK_SIZE = 8
L3_TARGET_COEFF = (4, 3)
L3_QUANTIZATION_STEP = 15
L3_BLOCKS_PER_BIT = 6
L3_FRAME_INTERVAL = 3
L3_MIN_FRAME_AGREEMENT = 0.45

# ---- Fusion Decision ----
FUSION_MIN_AGREEING_LAYERS = 2
FUSION_OVERALL_THRESHOLD = 0.45
LAYER_AGREEMENT_THRESHOLDS = {
    "layer1": 0.35,
    "layer2": 0.40,
    "layer3": 0.35,
}

# ---- Paths ----
REGISTRY_PATH = "session_registry.json"
DEMO_VIDEOS_DIR = "demo_videos"
WATERMARKED_DIR = "watermarked_outputs"
TEMP_DIR = "temp_processing"

# ---- Server ----
HOST = "0.0.0.0"
PORT = 8001
