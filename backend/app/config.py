from pathlib import Path
import os

from dotenv import load_dotenv


# Project root:
# PromptGuard-AI/
ROOT_DIR = Path(__file__).resolve().parents[2]

ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma"
CACHE_RESPONSE_FILE = DATA_DIR / "cache_responses.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# OpenAI
# -----------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LOW_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MEDIUM_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
HIGH_MODEL = os.getenv("OPENAI_MODEL", os.getenv("HIGH_MODEL", "gpt-5.4"))

MODERATION_MODEL = os.getenv(
    "MODERATION_MODEL",
    "omni-moderation-latest",
)


# -----------------------------
# Routing
# -----------------------------

ROUTER_MODEL_PATH = Path(__file__).resolve().parent / "router" / "artifacts" / "tier_classifier.joblib"


# -----------------------------
# Semantic cache
# -----------------------------

CACHE_SIMILARITY_THRESHOLD = float(
    os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.90")
)


# -----------------------------
# Request limits
# -----------------------------

MAX_CONTENT_CHARS = int(
    os.getenv("MAX_CONTENT_CHARS", "120000")
)

MAX_OUTPUT_TOKENS = int(
    os.getenv("MAX_OUTPUT_TOKENS", "1200")
)


# -----------------------------
# Frontend
# -----------------------------

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000",
)
