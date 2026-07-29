"""HTTP API.

Sync endpoints on purpose: FastAPI runs `def` handlers in a threadpool, and
every dependency here (LangGraph's sync checkpointer, psycopg, fastembed) is
sync. Async handlers would need an async checkpointer and pool for no gain at
this scale.

The routers are split by what they are about — the review, the knowledge, the
microphone, the process — and each one only ever calls `knowli.application`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ... import config, wiring
from ...application import knowledge_bases as kb_service
from ...application import review as review_service
from . import health, knowledge, review, speech


@asynccontextmanager
async def lifespan(_: FastAPI):
    wiring.init_storage()
    review_service.graph()  # builds the graph and runs the checkpointer migrations
    yield


def _status(code: int):
    """The application layer raises its own exceptions; HTTP is where they get a
    number. Keeps every route free of try/except for the same three cases."""

    def handler(_: Request, error: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=code)

    return handler


def create_app() -> FastAPI:
    app = FastAPI(
        title="Knowli",
        version="0.2.0",
        description="Human-in-the-loop knowledge capture over a pgvector hybrid RAG.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(review_service.SessionNotFound, _status(404))
    app.add_exception_handler(review_service.SessionNotWaiting, _status(409))
    app.add_exception_handler(review_service.SessionFinished, _status(409))
    # A slug nobody has is a 404 on every route that takes one. Never a quiet
    # fall back to the default: writing a claim into the wrong knowledge base
    # is a mistake you find out about months later, from a wrong answer.
    app.add_exception_handler(kb_service.KnowledgeBaseNotFound, _status(404))
    app.add_exception_handler(kb_service.SlugTaken, _status(409))

    app.include_router(review.router)
    app.include_router(knowledge.router)
    app.include_router(speech.router)
    app.include_router(health.router)
    return app
