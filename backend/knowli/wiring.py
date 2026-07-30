"""The composition root for application services."""

import functools

from . import config
from .application.auth import AuthService
from .application.review import ContributionService
from .infrastructure.embedding.embedder import ConfiguredEmbedder
from .infrastructure.llm.openai import OpenAIModel
from .infrastructure.postgres.repository import PostgresStore

store = PostgresStore()
auth_service = AuthService(store, session_days=config.SESSION_DAYS)


def checkpointer():
    """LangGraph's Postgres checkpointer, retained until its service migrates."""
    from langgraph.checkpoint.postgres import PostgresSaver

    from .infrastructure.postgres.pool import pool

    saver = PostgresSaver(pool.checkpoint_pool())
    saver.setup()
    return saver


@functools.cache
def contribution_service() -> ContributionService:
    return ContributionService(
        store,
        OpenAIModel(),
        ConfiguredEmbedder(),
        checkpointer(),
    )
