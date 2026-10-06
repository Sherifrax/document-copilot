# Production deployment guide: Railway

This guide deploys Document Copilot as two Railway services:

- **Backend**: FastAPI + Uvicorn, using Supabase Postgres/Auth and OpenAI.
- **Frontend**: Vite + React SPA, served by Vite's production preview server.

The database remains in Supabase. Railway is only hosting the application services.

## 1. Before you deploy

Make sure these are ready:

- A GitHub repository containing this project.
- A Supabase project and its API/database credentials.
- An OpenAI API key and the chat model you want to use.
- A Railway account connected to the GitHub repository.
- The corpus has been ingested into Supabase if you want production chat answers immediately.

Do not commit either `.env` file. The repository ignores them already. Never put
`SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, or `OPENAI_API_KEY` in the frontend
service.

## 2. Create the Railway project and services

1. In Railway, create a new project and choose **Deploy from GitHub repo**.
2. Select the repository for Document Copilot.
3. Rename the first service to `document-copilot-backend`.
4. Add a second service from the same repository and rename it to
   `document-copilot-frontend`.
5. For each service, set its **Root Directory**. This is important because the
   repository contains two independent applications:

   | Service | Root Directory |
   | --- | --- |
   | Backend | `/backend` |
   | Frontend | `/frontend` |

Railway should redeploy a service when files under its root directory change.

## 3. Configure the backend service

In the backend service's **Variables** tab, add these variables:

```text
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL=postgresql://postgres:YOUR_URL_ENCODED_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
ALLOWED_ORIGINS=https://YOUR_FRONTEND_DOMAIN
```

Use the Supabase **direct** database connection or the **session pooler** on
port `5432`. Do not use the transaction pooler on port `6543`: Alembic rejects
it. URL-encode special characters in the database password.

Set the backend service commands as follows. Railway normally detects Python
and `uv.lock` automatically, but setting these explicitly makes the deployment
repeatable:

- **Build Command**: `uv sync --frozen --no-dev`
- **Start Command**: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`

The backend reads `$PORT` from Railway. Do not hard-code port `8000` in the
production start command.

## 4. Run the database migrations

Run migrations once before the backend serves production traffic. In the
backend service's **Settings**, set the Railway **Pre-deploy Command** to:

```bash
uv run alembic upgrade head
```

The pre-deploy command uses the backend variables, including `DATABASE_URL`.
After the first successful deployment, verify the migration locally or from a
temporary Railway shell with:

```bash
uv run alembic current
```

Do not manually create or alter application tables in the Supabase dashboard;
Alembic migrations are the source of truth.

If your Railway plan/UI does not expose a pre-deploy command, run the same
command from a one-off Railway shell/job using the backend environment
variables, then deploy the backend. Do not put migrations in the web process's
start command because a restart could run them repeatedly while the service is
starting.

## 5. Deploy the backend and create its public URL

1. Deploy the backend service.
2. In **Settings → Networking**, generate a Railway public domain, for example
   `document-copilot-backend-production.up.railway.app`.
3. Check the health endpoint:

```bash
curl https://YOUR_BACKEND_DOMAIN/health
```

Expected response:

```json
{"status":"ok"}
```

Keep this backend URL available for the frontend configuration.

## 6. Configure the frontend service

In the frontend service's **Variables** tab, add:

```text
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

These values are embedded into the browser bundle during the build. Any change
to them requires a new frontend deployment.

Set the frontend service commands:

- **Build Command**: `pnpm install --frozen-lockfile && pnpm build`
- **Start Command**: `pnpm exec vite preview --host 0.0.0.0 --port $PORT`

Railway should detect `pnpm-lock.yaml`. If it does not, set the service's
package manager/runtime to Node.js and use a Node 20+ runtime.

Generate a public Railway domain for the frontend service as well. Once you
have it, update the backend variable:

```text
ALLOWED_ORIGINS=https://YOUR_FRONTEND_DOMAIN
```

Then redeploy the backend. For local testing plus production, use a comma-
separated value instead, for example:

```text
ALLOWED_ORIGINS=http://localhost:5173,https://YOUR_FRONTEND_DOMAIN
```

Do not include a trailing slash in either the frontend API URL or an allowed
origin.

## 7. Supabase Auth settings

In Supabase **Authentication → URL Configuration**:

1. Set **Site URL** to the frontend Railway URL.
2. Add the frontend Railway URL to **Redirect URLs**.
3. Keep email authentication enabled, since this application uses email auth.

If you later attach a custom domain, add that domain to both the Supabase
redirect URLs and the backend `ALLOWED_ORIGINS` value.

## 8. Production verification checklist

Run these checks after both services are deployed:

- `GET https://YOUR_BACKEND_DOMAIN/health` returns `{"status":"ok"}`.
- Opening the frontend domain loads the login page without a blank screen.
- Sign-up and sign-in work through Supabase Auth.
- The browser can call the backend without a CORS error.
- Creating a chat and sending a question returns a streamed answer.
- Citations open and point to the expected source passages.
- Railway logs contain no missing-environment-variable errors.
- Supabase contains the expected migration version and ingested corpus.
- The backend logs do not expose API keys, bearer tokens, prompts, answers, or filing contents.

For a quick browser/API check, open the backend `/docs` URL temporarily. Remove
or protect public API documentation if the deployment requires a restricted
surface.

## 9. Updating the application

Normal updates are pushed to GitHub and deployed by Railway:

1. Push the change.
2. Let Railway build and deploy the affected service.
3. If a migration changed, let the backend pre-deploy command run
   `uv run alembic upgrade head`.
4. If frontend environment values changed, redeploy the frontend so Vite
   rebuilds the browser bundle.
5. Re-run `/health` and the sign-in/chat smoke test.

For a schema change, review the generated Alembic migration before merging it.
Back up important production data before destructive migrations. Avoid
`alembic downgrade` in production unless the rollback has been explicitly
reviewed for data loss.

## 10. Common deployment problems

### Backend fails during startup with missing settings

Check every backend variable in Section 3. The backend intentionally fails fast
when required configuration is missing.

### Alembic rejects the database URL

Confirm that `DATABASE_URL` uses the Supabase direct connection or session
pooler on port `5432`, not the transaction pooler on `6543`. Also confirm that
the password is URL-encoded.

### Frontend shows a CORS or network error

Check all three values: the frontend `VITE_API_BASE_URL`, the backend
`ALLOWED_ORIGINS`, and the exact public frontend origin. After changing a
`VITE_*` variable, redeploy the frontend. After changing `ALLOWED_ORIGINS`,
redeploy the backend.

### Frontend displays a missing environment variable error

The Vite build did not receive one of `VITE_API_BASE_URL`,
`VITE_SUPABASE_URL`, or `VITE_SUPABASE_ANON_KEY`. Add it to the frontend
service, then trigger a new deployment.

### Railway reports that the service is listening on the wrong port

Use `$PORT` in the start command and bind to `0.0.0.0`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
pnpm exec vite preview --host 0.0.0.0 --port $PORT
```

### Chat works locally but not in production

Check the backend logs, OpenAI model/key configuration, Supabase corpus
ingestion, and the browser's network request URL. The frontend must call the
Railway backend URL, not `http://localhost:8000`.
