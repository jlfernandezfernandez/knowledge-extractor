"""The composition root for the web application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from . import config
from .application.ask import AskService
from .application.auth import AuthService
from .application.interviews import InterviewService
from .application.review import ContributionService
from .domain.ports import Embedder, Model
from .infrastructure.embedding.embedder import ConfiguredEmbedder
from .infrastructure.e2e import E2EEmbedder, E2EModel
from .infrastructure.llm.openai import OpenAIModel
from .infrastructure.postgres.pool import create_checkpoint_pool, create_pool
from .infrastructure.postgres.repository import PostgresStore


@dataclass
class AppServices:
    """Application dependencies, allocated only by an authenticated request."""

    _pool: ConnectionPool | None = field(default=None, init=False)
    _checkpoint_pool: ConnectionPool | None = field(default=None, init=False)
    _store: PostgresStore | None = field(default=None, init=False)
    _model: Model | None = field(default=None, init=False)
    _embedder: Embedder | None = field(default=None, init=False)
    _checkpointer: Any | None = field(default=None, init=False)
    _auth: AuthService | None = field(default=None, init=False)
    _contributions: ContributionService | None = field(default=None, init=False)
    _ask: AskService | None = field(default=None, init=False)
    _interviews: InterviewService | None = field(default=None, init=False)

    @property
    def pool(self) -> ConnectionPool:
        if self._pool is None:
            self._pool = create_pool()
        return self._pool

    @property
    def checkpoint_pool(self) -> ConnectionPool:
        if self._checkpoint_pool is None:
            self._checkpoint_pool = create_checkpoint_pool()
        return self._checkpoint_pool

    @property
    def store(self) -> PostgresStore:
        if self._store is None:
            self._store = PostgresStore(self.pool)
        return self._store

    @property
    def model(self) -> Model:
        if self._model is None:
            self._model = E2EModel() if config.E2E_DEPENDENCIES else OpenAIModel()
        return self._model

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = E2EEmbedder() if config.E2E_DEPENDENCIES else ConfiguredEmbedder()
        return self._embedder

    @property
    def checkpointer(self) -> Any:
        if self._checkpointer is None:
            from langgraph.checkpoint.postgres import PostgresSaver

            self._checkpointer = PostgresSaver(self.checkpoint_pool)
            self._checkpointer.setup()
        return self._checkpointer

    @property
    def auth(self) -> AuthService:
        if self._auth is None:
            self._auth = AuthService(self.store, session_days=config.SESSION_DAYS)
        return self._auth

    @property
    def contributions(self) -> ContributionService:
        if self._contributions is None:
            self._contributions = ContributionService(
                self.store, self.model, self.embedder, self.checkpointer
            )
        return self._contributions

    @property
    def ask(self) -> AskService:
        if self._ask is None:
            self._ask = AskService(self.store, self.model, self.embedder)
        return self._ask

    @property
    def interviews(self) -> InterviewService:
        if self._interviews is None:
            self._interviews = InterviewService(self.store)
        return self._interviews

    def ready(self) -> bool:
        """A lightweight PostgreSQL probe; liveness must not depend on it."""
        try:
            with self.pool.connection(timeout=1) as connection:
                connection.execute("SELECT 1")
        except Exception:
            return False
        return True

    def close(self) -> None:
        """Release resources in reverse construction order."""
        for resource in (self._checkpointer, self._model):
            close = getattr(resource, "close", None)
            if callable(close):
                close()
        for connection_pool in (self._checkpoint_pool, self._pool):
            if connection_pool is not None:
                connection_pool.close()


def services(app: FastAPI) -> AppServices:
    """Return lifespan services, preserving simple ``create_app`` test callers."""
    if not hasattr(app.state, "services"):
        app.state.services = AppServices()
    return app.state.services


def speech_available() -> bool:
    """Check configured speech support without importing its optional engines."""
    from .infrastructure.speech.transcriber import available

    return available()


def create_transcriber():
    """Construct speech only after its websocket has accepted a supported client."""
    from .infrastructure.speech.transcriber import create

    return create()
