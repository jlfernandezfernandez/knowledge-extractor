"""The HTTP application while the remaining feature routers are migrated."""

from fastapi import FastAPI

from . import auth
from .errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Knowli", version="0.2.0")
    register_error_handlers(app)
    app.include_router(auth.router)
    return app
