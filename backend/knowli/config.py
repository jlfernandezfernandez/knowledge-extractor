"""Configuration read from the environment."""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://knowli:knowli@localhost:5432/knowli"
)
MODEL_BASE_URL = os.environ.get("MODEL_BASE_URL", "http://host.docker.internal:11434/v1")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "ollama")
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3.5:9b")
# Local reasoning models (qwen3.5) otherwise spend minutes emitting thinking tokens
# with an empty `content`, which stalls the answer stream. Empty string = provider default.
MODEL_REASONING_EFFORT = os.environ.get("MODEL_REASONING_EFFORT", "")
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBED_DIM = int(os.environ.get("EMBED_DIM", "384"))
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "14"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
TRANSCRIPTION_MODEL = os.environ.get("TRANSCRIPTION_MODEL", "Systran/faster-whisper-small")
TRANSCRIPTION_API_KEY = os.environ.get("TRANSCRIPTION_API_KEY", "local")
TRANSCRIPTION_BASE_URL = os.environ.get(
    "TRANSCRIPTION_BASE_URL", "http://host.docker.internal:8000/v1"
)
