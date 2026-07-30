"""Small, transactional runner for Knowli's numbered PostgreSQL migrations."""

from importlib import resources

from psycopg_pool import ConnectionPool


def run_migrations(pool: ConnectionPool) -> None:
    """Apply each embedded migration once, while holding a database-wide lock."""
    files = sorted(
        (path for path in resources.files(__package__).joinpath("migrations").iterdir()
         if path.name.endswith(".sql")),
        key=lambda path: path.name,
    )
    with pool.connection() as connection:
        original_autocommit = connection.autocommit
        connection.autocommit = True
        connection.execute("SELECT pg_advisory_lock(hashtext('knowli-migrations'))")
        try:
            with connection.transaction():
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migration "
                    "(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
                )
            for path in files:
                version = int(path.name.partition("_")[0])
                with connection.transaction():
                    connection.execute("SELECT pg_advisory_xact_lock(hashtext('knowli-migrations'))")
                    applied = connection.execute(
                        "SELECT 1 FROM schema_migration WHERE version = %s", (version,)
                    ).fetchone()
                    if applied:
                        continue
                    connection.execute(path.read_text())
                    connection.execute(
                        "INSERT INTO schema_migration (version) VALUES (%s)", (version,)
                    )
        finally:
            try:
                connection.execute("SELECT pg_advisory_unlock(hashtext('knowli-migrations'))")
            finally:
                connection.autocommit = original_autocommit
