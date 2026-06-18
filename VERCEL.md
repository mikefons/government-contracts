# Deploying Chancery on Vercel

Everything runs on Vercel: the React SPA as static output, and FastAPI as a Python
serverless function. No container host required. State that can't live in a serverless
process has been externalised:

- Vendor ontologies persist in Postgres (not process memory).
- The seeded federal graph is deterministic and rebuilt per cold start (read-only).
- The in-memory rate limiter and the APScheduler ingest are disabled in serverless mode.

## 1. Provision a serverless Postgres
Use Neon, Vercel Postgres, or Supabase. Copy the **pooled** connection string
(serverless functions open many short-lived connections), e.g.
`postgresql+psycopg2://USER:PASS@HOST/db?sslmode=require`.

## 2. Set Vercel project environment variables
Required:
```
DATABASE_URL      postgresql+psycopg2://...pooled...
SECRET_KEY        (openssl rand -hex 32)
ADMIN_EMAIL       admin@chancery.local
ADMIN_PASSWORD    (a strong value)
SERVERLESS        true
RUN_CREATE_ALL    true
```
Optional:
```
ANTHROPIC_API_KEY sk-ant-...        (live ontology/agent reasoning)
ANTHROPIC_MODEL   claude-sonnet-4-6
```
`SERVERLESS=true` disables the in-process rate limiter and scheduler and switches the DB
to non-pooled connections. `RUN_CREATE_ALL=true` lets the app create tables on first
request (Alembic's migrate-on-start isn't available in a serverless function).

## 3. Deploy
With the Vercel CLI from the repo root:
```
npm i -g vercel
vercel        # preview
vercel --prod # production
```
Or connect the GitHub repo in the Vercel dashboard and it builds on push. The included
`vercel.json` builds the frontend (`frontend/dist`), serves the API from
`api/index.py`, bundles the `backend/` package, and rewrites `/api/*` to the function
with an SPA fallback for everything else. Because the API is same-origin, no CORS config
is needed.

## 4. First load
Open the deployment URL and sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`. The first
request creates the schema, seeds reference data, and bootstraps the admin.

## Honest caveats
- A real `vercel deploy` is the final verification — it could not be run from the build
  sandbox. The app logic is verified locally in serverless mode (imported via
  `api/index.py`, run without lifespan, ontology persistence confirmed across requests).
  The parts to watch on first deploy are the `@vercel/python` ASGI serving and the
  `includeFiles: backend/**` bundling.
- No distributed rate limiting on Vercel — add Upstash Redis if you need it.
- Periodic ingest won't run serverless; use a Vercel Cron hitting an admin endpoint.
- Sovereignty note: Vercel is US-hosted. For an OFFICIAL-SENSITIVE posture, prefer a
  UK/EU region on a container host (see DEPLOY.md) over serverless on US infrastructure.
