"""Configuration, read once from the environment (and a .env file if present)."""

import os
from pathlib import Path

# ponytail: 5-line .env reader instead of a python-dotenv dependency.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ke:ke@localhost:5432/ke")

LLM_API_BASE = os.environ.get("LLM_API_BASE", "http://localhost:11434/v1").rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "not-needed")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3")

EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBED_DIM = int(os.environ.get("EMBED_DIM", "384"))
EMBED_API_BASE = os.environ.get("EMBED_API_BASE", "").rstrip("/")
EMBED_API_KEY = os.environ.get("EMBED_API_KEY", "not-needed")

CONFLICT_TOP_K = int(os.environ.get("CONFLICT_TOP_K", "5"))
CONFLICT_MAX_DISTANCE = float(os.environ.get("CONFLICT_MAX_DISTANCE", "0.55"))

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
