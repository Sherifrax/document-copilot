# Backend

Run these commands from `backend/`.

## Setup

Copy `.env.example` to `.env` and fill in your credentials, then install dependencies and the local `app` package:

```bash
uv sync
```

## Run the API

```bash
uv run uvicorn app.main:app --reload
```

Health check: <http://localhost:8000/health>. API docs: <http://localhost:8000/docs>.
Changes reload automatically; press `Ctrl+C` to stop.

## Dependencies and checks

```bash
uv add <package>          # Runtime dependency
uv add --dev <package>    # Development dependency
uv run ruff check app
```

## Notebooks

Select `backend/.venv/bin/python` or the **Document Copilot Backend** kernel.
After `uv sync`, restart the kernel if imports fail. Settings live in `app/config.py`.

## Database migrations

Alembic reads `DATABASE_URL` through `app/config.py` and uses psycopg.
Use the Supabase direct connection or session pooler (port 5432), never the
transaction pooler (port 6543). The migration role needs permission to create
extensions, tables, policies, and grants. Supabase's `auth.users`, `auth.uid()`,
and `anon`, `authenticated`, and `service_role` roles must already exist.

Prepare SQL for review without connecting to or changing the database:

```bash
uv run alembic upgrade head --sql > /tmp/document-copilot-upgrade.sql
uv run alembic downgrade 0001:base --sql > /tmp/document-copilot-downgrade.sql
```

The first migration creates all six application tables, `vector(1536)`, a stored
English `tsvector`, a cosine HNSW index, and a GIN full-text index. It enables
RLS on all application tables. Authenticated users can read their own user
record and manage only their own threads, messages, and citations; ownership
is checked on both existing and replacement rows. They can read the shared
filing corpus but cannot write it. Anonymous access is revoked. User records
and corpus writes are handled by the backend service role.

The service role bypasses RLS, so backend operations using it must still enforce
ownership. No user provisioning trigger is included; the auth integration will
create the application user record before creating a thread.

After approval, apply the reviewed migration:

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Then verify ownership with two authenticated users, including attempts to read
or move another user's messages/citations. Offline SQL validation does not
exercise PostgreSQL or RLS. Autogenerate is limited to application-owned tables;
review its output and add policy/extension changes explicitly.

`uv run alembic downgrade base` deletes all application tables and their data.
It leaves the potentially shared `vector` extension and Supabase Auth intact.
