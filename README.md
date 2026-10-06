# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

Create the two environment files from the checked-in examples, then fill in the
values from Supabase and OpenAI:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Start the backend in one terminal:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
pnpm install
pnpm dev
```

Required backend variables are listed in [backend/.env.example](backend/.env.example):
Supabase URL/keys, a direct or session Postgres `DATABASE_URL`, OpenAI key and
models, and `ALLOWED_ORIGINS`. Required browser-safe variables are listed in
[frontend/.env.example](frontend/.env.example): `VITE_API_BASE_URL`,
`VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`. Never put the service-role
key or database URL in the frontend file.

Check the API before opening the SPA:

```bash
curl http://localhost:8000/health
```

Expected response: `{"status":"ok"}`. Backend logs include a request ID,
duration, and chat-turn outcome; do not log prompts, answers, bearer tokens, or
filing contents.

Setup guides:

- [Supabase](docs/guides/supabase-setup.md) — account, hosted project (dashboard or CLI)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)

## Sample SEC data

Use the standalone downloader to fetch a small local 10-K sample from SEC EDGAR.
Edit the params at the top of `data/download.py`, especially `USER_AGENT`, then run:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into year folders under `data/downloads/` and writes a `manifest.json`.
Downloaded files are gitignored; the `data/` folder itself stays in git for the script and notes.

## Updating and ingesting the corpus

The committed `data/markdown/manifest.json` is the current 25-filing pilot
corpus (Apple, Amazon, Alphabet, Microsoft, and NVIDIA; fiscal years 2021–2025).
To refresh it from SEC EDGAR, update the contact in `data/download.py`, then run:

```bash
uv run data/download.py
uv run --project backend data/convert_to_markdown.py
cd backend
uv run python -m ingest.source_documents
uv run python -m ingest.chunks plan
uv run python -m ingest.chunks pilot       # optional paid sanity check
uv run python -m ingest.chunks run --confirm
```

`source_documents` is idempotent by SEC accession number. `chunks plan` makes
no API calls or writes; the full chunk run only inserts missing chunks and
requires the explicit `--confirm` switch.

## Pilot verification

Run the ten client-brief retrieval probes in isolation after ingestion:

```bash
cd backend
uv run python scripts/evaluate_retrieval.py
```

For each probe, record whether the returned passages cover the requested
company/year scope, have a page number or section, and support the claim. Then
manually ask the exact questions in [docs/client-brief.md](docs/client-brief.md)
through the browser and verify every answer has clickable citations and an
underlying passage. The pilot acceptance sheet and persistence/latency checks
are in [docs/pilot-readiness.md](docs/pilot-readiness.md).
