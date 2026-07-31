"""Unified composition root for PostgreSQL repository implementations."""

from psycopg_pool import ConnectionPool

from .contribution_repository import PostgresContributionStore
from .interview_repository import PostgresInterviewStore
from .user_repository import PostgresUserStore


class PostgresStore(PostgresUserStore, PostgresInterviewStore, PostgresContributionStore):
    """Composite repository providing all domain stores over a shared PostgreSQL pool."""

    def __init__(self, connection_pool: ConnectionPool | None = None):
        PostgresUserStore.__init__(self, connection_pool)
        PostgresInterviewStore.__init__(self, connection_pool)
        PostgresContributionStore.__init__(self, connection_pool)


__all__ = [
    "PostgresContributionStore",
    "PostgresInterviewStore",
    "PostgresStore",
    "PostgresUserStore",
]
