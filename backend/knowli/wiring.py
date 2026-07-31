"""The composition root for the web application."""

from __future__ import annotations

from functools import cached_property
from typing import Any

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from . import config
from .application.ask import AskService, HistoryService
from .application.auth import AuthService
from .application.interviews import InterviewService
from .application.review import ContributionService
from .domain.ports import (
    ContributionStore,
    Embedder,
    InterviewStore,
    Model,
    SessionStore,
    Transcriber,
)
from .infrastructure.embedding import ConfiguredEmbedder
from .infrastructure.llm.openai import OpenAICompatibleModel
from .infrastructure.postgres.contribution_repository import PostgresContributionStore
from .infrastructure.postgres.interview_repository import PostgresInterviewStore
from .infrastructure.postgres.pool import create_checkpoint_pool, create_pool
from .infrastructure.postgres.repository import PostgresStore
from .infrastructure.postgres.user_repository import PostgresUserStore


class AppServices:
    """Application dependencies, allocated only by an authenticated request."""

    @cached_property
    def pool(self) -> ConnectionPool:
        return create_pool()

    @cached_property
    def checkpoint_pool(self) -> ConnectionPool:
        return create_checkpoint_pool()

    @cached_property
    def user_store(self) -> SessionStore:
        return PostgresUserStore(self.pool)

    @cached_property
    def interview_store(self) -> InterviewStore:
        return PostgresInterviewStore(self.pool)

    @cached_property
    def contribution_store(self) -> ContributionStore:
        return PostgresContributionStore(self.pool)

    @cached_property
    def store(self) -> PostgresStore:
        return PostgresStore(self.pool)

    @cached_property
    def model(self) -> Model:
        return OpenAICompatibleModel(checkpointer=self.checkpointer)

    @cached_property
    def embedder(self) -> Embedder:
        return ConfiguredEmbedder()

    @cached_property
    def checkpointer(self) -> Any:
        from langgraph.checkpoint.postgres import PostgresSaver

        checkpointer = PostgresSaver(self.checkpoint_pool)
        checkpointer.setup()
        return checkpointer

    @cached_property
    def auth(self) -> AuthService:
        return AuthService(self.user_store, session_days=config.SESSION_DAYS)

    @cached_property
    def contributions(self) -> ContributionService:
        return ContributionService(
            self.contribution_store, self.model, self.embedder, self.checkpointer
        )

    @cached_property
    def ask(self) -> AskService:
        return AskService(
            self.contribution_store, self.model, self.embedder, self.interview_store
        )

    @cached_property
    def history(self) -> HistoryService:
        return HistoryService(self.contribution_store)

    @cached_property
    def interviews(self) -> InterviewService:
        return InterviewService(self.interview_store)

    @cached_property
    def transcriber(self) -> Transcriber:
        from .infrastructure.transcription import create_transcriber

        return create_transcriber()

    def ready(self) -> bool:
        """A lightweight PostgreSQL probe; liveness must not depend on it."""
        try:
            with self.pool.connection(timeout=1) as connection:
                connection.execute("SELECT 1")
        except Exception:
            return False
        return True

    def warmup(self) -> None:
        """Pre-initialize checkpointer DDL setup and embedding model during server startup."""
        _ = self.checkpointer
        embedder = self.embedder
        warmup = getattr(embedder, "warmup", None)
        if callable(warmup):
            warmup()

    def close(self) -> None:
        """Release resources in reverse construction order."""
        for name in ("checkpointer", "model", "transcriber"):
            resource = self.__dict__.get(name)
            close = getattr(resource, "close", None)
            if callable(close):
                close()
        for name in ("checkpoint_pool", "pool"):
            connection_pool = self.__dict__.get(name)
            if connection_pool is not None:
                connection_pool.close()


def services(app: FastAPI) -> AppServices:
    """Return lifespan services, preserving simple ``create_app`` test callers."""
    if not hasattr(app.state, "services"):
        app.state.services = AppServices()
    return app.state.services
