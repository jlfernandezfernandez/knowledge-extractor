"""Liveness, readiness, and the effective local configuration."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from ... import config, wiring

router = APIRouter(prefix="/api/health", tags=["ops"])


@router.get("/live")
def live() -> dict[str, bool]:
    """The process is accepting requests; it deliberately does not touch PostgreSQL."""
    return {"ok": True}


@router.get("/ready", response_model=None)
def ready(request: Request):
    """Readiness requires a usable database connection."""
    if wiring.services(request.app).ready():
        return {"ok": True}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"ok": False, "code": "not_ready"},
    )


@router.get("")
def health() -> dict:
    """Expose configured values without claiming optional services are running."""
    return {
        "ok": True,
        "openai": {
            "model": config.OPENAI_MODEL,
            "api_key_configured": bool(config.OPENAI_API_KEY),
        },
        "embeddings": {"model": config.EMBEDDING_MODEL, "dim": config.EMBED_DIM},
        "speech": {"provider": config.SPEECH_PROVIDER},
    }
