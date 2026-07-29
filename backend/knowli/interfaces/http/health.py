"""Is anything actually plugged in? Answers with what is configured, not just "ok"."""

from fastapi import APIRouter

from ... import config, wiring

router = APIRouter(tags=["ops"])


@router.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "speech": {
            "provider": config.SPEECH_PROVIDER,
            "available": wiring.speech_available(),
        },
        "llm": {"model": config.LLM_MODEL, "base_url": config.LLM_BASE_URL},
        "embeddings": {
            "provider": config.EMBED_PROVIDER,
            "model": config.EMBED_MODEL,
            "dim": config.EMBED_DIM,
        },
    }
