"""The composition root for the services migrated so far."""

from . import config
from .application.auth import AuthService
from .domain.ports import SessionStore
from .infrastructure.postgres.repository import PostgresStore

store: SessionStore = PostgresStore()
auth_service = AuthService(store, session_days=config.SESSION_DAYS)


def checkpointer():
    """LangGraph's Postgres checkpointer, retained until its service migrates."""
    from langgraph.checkpoint.postgres import PostgresSaver

    from .infrastructure.postgres.pool import pool

    saver = PostgresSaver(pool.checkpoint_pool())
    saver.setup()
    return saver
