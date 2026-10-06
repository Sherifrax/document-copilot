"""Async Postgres construction for request-path database work."""

from pgvector.psycopg import register_vector_async
from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def async_database_url(raw_url: str) -> URL:
    """Validate and normalize a PostgreSQL URL for psycopg's async driver."""
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must be a PostgreSQL connection")
    return url.set(drivername="postgresql+psycopg")


def create_postgres_engine(raw_url: str) -> AsyncEngine:
    """Create an async engine with pgvector registered on every connection."""
    engine = create_async_engine(async_database_url(raw_url), pool_pre_ping=True)

    @event.listens_for(engine.sync_engine, "connect")
    def register_vector(dbapi_connection: object, _: object) -> None:
        dbapi_connection.run_async(register_vector_async)  # type: ignore[attr-defined]

    return engine


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create sessions that do not expire loaded values after commit."""
    return async_sessionmaker(engine, expire_on_commit=False)
