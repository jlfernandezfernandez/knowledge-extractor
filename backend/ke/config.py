"""Configuration, read once from the environment (and a .env file if present)."""

import os
from pathlib import Path

# ponytail: 6-line .env reader instead of a python-dotenv dependency.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ke:ke@localhost:5432/ke")

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b")
# See ke/llm.py for why these three defaults are what they are.
LLM_STRUCTURED_METHOD = os.environ.get("LLM_STRUCTURED_METHOD", "json_schema")
LLM_REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "none").strip()
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2048"))

EMBED_PROVIDER = os.environ.get("EMBED_PROVIDER", "local")
EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBED_DIM = int(os.environ.get("EMBED_DIM", "384"))
EMBED_BASE_URL = os.environ.get("EMBED_BASE_URL", "http://localhost:11434/v1")
EMBED_API_KEY = os.environ.get("EMBED_API_KEY", "ollama")

RRF_K = int(os.environ.get("RRF_K", "60"))
RETRIEVE_TOP_K = int(os.environ.get("RETRIEVE_TOP_K", "10"))
CONFLICT_TOP_K = int(os.environ.get("CONFLICT_TOP_K", "5"))
CONFLICT_MAX_DISTANCE = float(os.environ.get("CONFLICT_MAX_DISTANCE", "0.55"))

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
REVIEW_BASE_URL = os.environ.get("REVIEW_BASE_URL", "http://localhost:5173").rstrip("/")
