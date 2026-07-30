"""The single HTTP application for Knowli."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ... import wiring
from . import ask, auth, health, history, interviews, review, speech
from .errors import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = wiring.AppServices()
    try:
        yield
    finally:
        app.state.services.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Knowli", version="0.2.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(auth.users_router)
    app.include_router(review.router)
    app.include_router(interviews.router)
    app.include_router(ask.router)
    app.include_router(history.router)
    app.include_router(speech.router)
    return app
