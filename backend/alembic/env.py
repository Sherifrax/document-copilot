"""Alembic configuration for the application-owned public tables."""

from logging.config import fileConfig
from typing import Any

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL, make_url

from alembic import context
from app.config import settings
from app.database.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, parent_names: dict[str, Any]) -> bool:
    # Never propose dropping Supabase-owned or unrelated tables.
    if type_ == "schema":
        return name in (None, "public")
    if type_ == "table":
        return name in target_metadata.tables
    return True


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    from pgvector.sqlalchemy import Vector

    if type_ == "type" and isinstance(obj, Vector):
        autogen_context.imports.add("from pgvector.sqlalchemy import Vector")
        return f"Vector({obj.dim})"
    return False


def migration_url() -> URL:
    url = make_url(settings.database_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must be a PostgreSQL direct/session connection")
    if url.port == 6543 or dict(url.query).get("pgbouncer") == "true":
        raise ValueError(
            "Alembic requires a direct/session connection, not a transaction pooler"
        )
    return url.set(drivername="postgresql+psycopg")


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(migration_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # Resolve public tables and pgvector whether Supabase installed it in
        # public or its conventional extensions schema.
        connection.exec_driver_sql("SET search_path TO public, extensions")
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
