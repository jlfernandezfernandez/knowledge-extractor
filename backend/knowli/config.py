"""Configuration read from the environment."""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://knowli:knowli@localhost:5432/knowli"
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBED_DIM = int(os.environ.get("EMBED_DIM", "384"))
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "14"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
SPEECH_PROVIDER = os.environ.get("SPEECH_PROVIDER")
SPEECH_MODEL_DIR = os.environ.get("SPEECH_MODEL_DIR", "")
SPEECH_THREADS = int(os.environ.get("SPEECH_THREADS", "4"))
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
