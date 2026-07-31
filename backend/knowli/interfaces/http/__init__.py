"""The single HTTP application for Knowli."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ... import __version__, wiring
from . import ask, auth, health, history, interviews, review, transcription
from .errors import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    services = wiring.AppServices()
    app.state.services = services
    services.warmup()
    try:
        yield
    finally:
        app.state.services.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Knowli", version=__version__, lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(auth.users_router)
    app.include_router(review.router)
    app.include_router(transcription.router)
    app.include_router(interviews.router)
    app.include_router(ask.router)
    app.include_router(history.router)
    return app
