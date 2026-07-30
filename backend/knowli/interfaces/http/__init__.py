"""The HTTP application while the remaining feature routers are migrated."""

from fastapi import FastAPI

from . import ask, auth, history, interviews, review
from .errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Knowli", version="0.2.0")
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(review.router)
    app.include_router(interviews.router)
    app.include_router(ask.router)
    app.include_router(history.router)
    return app
