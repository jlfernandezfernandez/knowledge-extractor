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

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://knowli:knowli@localhost:5432/knowli"
)

# The workspace and knowledge base created on startup if they are not there, and
# used by anything that does not name one. Slugs, not display names: everything
# addresses a knowledge base by slug. A solo user never has to know either of
# these exists — which is the point of having a default at all.
DEFAULT_WORKSPACE = os.environ.get("DEFAULT_WORKSPACE", "default")
DEFAULT_KNOWLEDGE_BASE = os.environ.get("DEFAULT_KNOWLEDGE_BASE", "personal")

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.5:9b")
# See knowli/infrastructure/llm/chat_model.py for why these three defaults are
# what they are.
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

# --- Speech to text ---
# parakeet = NVIDIA Parakeet TDT 0.6B v3 via sherpa-onnx: 25 European
#            languages, auto language ID, ~10x realtime on CPU, live segments.
# whisper  = faster-whisper, batch only.
SPEECH_PROVIDER = os.environ.get("SPEECH_PROVIDER", "parakeet")
SPEECH_MODEL_DIR = os.environ.get(
    "SPEECH_MODEL_DIR",
    "~/Library/Application Support/Orca/speech-models/parakeet-tdt-0.6b-v3-int8",
)
SPEECH_THREADS = int(os.environ.get("SPEECH_THREADS", "4"))
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
REVIEW_BASE_URL = os.environ.get("REVIEW_BASE_URL", "http://localhost:5173").rstrip("/")
