# Chancery

A sovereign **UK/EU public-sector procurement intelligence & capture platform** —
the architecture of Govly (Opportunities · Awards · Signals · Capture · Automate),
re-pointed at Crown Commercial Service frameworks, Find a Tender, MOD/DE&S, NHS,
devolved government and EU TED.

Full stack: **FastAPI + Postgres** backend (JWT auth, RBAC, append-only audit log,
Alembic migrations), **React + Vite** frontend, plus an **intelligence engine** (graph
model, vendor ontology, 0–100 opportunity scoring). See `DEPLOY.md` and `INTEL.md`.

## Quick start (from GitHub)

```bash
git clone https://github.com/mikefons/government-contracts.git chancery
cd chancery
cp .env.example .env
```

Set your secrets in `.env` (on macOS these generate strong values automatically):

```bash
sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env
sed -i '' "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 16)|" .env
sed -i '' "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$(openssl rand -hex 8)|" .env
```

Then bring it up and sign in:

```bash
docker compose up --build -d
```

App → http://localhost:8080 · API docs → http://localhost:8000/docs
Login with `admin@chancery.local` and the `ADMIN_PASSWORD` from your `.env`
(`grep ADMIN_PASSWORD .env`). Run the tests with `cd backend && pip install -r requirements.txt && pytest`.

`.env` is git-ignored — your secrets are never committed.

```
chancery/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── main.py          REST API (all endpoints) + startup seed
│   │   ├── models.py        SQLAlchemy ORM
│   │   ├── schemas.py       Pydantic contract
│   │   ├── database.py      engine / session (SQLite, Postgres-ready)
│   │   ├── seed.py          synthetic UK/EU dataset (idempotent)
│   │   ├── agent.py         capture analyst — Anthropic | Ollama | offline
│   │   └── ingest.py        live OCDS pull from Find a Tender
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                React + Vite SPA
│   ├── src/{App.jsx, api.js, styles.css, main.jsx}
│   ├── vite.config.js       dev proxy /api → :8000
│   ├── nginx.conf           prod: serve SPA + proxy /api → backend
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Run it

### Docker (one command)
```bash
cp .env.example .env          # optional: add ANTHROPIC_API_KEY or OLLAMA_HOST
docker compose up --build
```
- App  → http://localhost:8080
- API  → http://localhost:8000/api
- Docs → http://localhost:8000/docs

### Local dev
```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173, proxies /api → :8000
```
The database seeds itself on first boot.

## The agent

`POST /api/agent` resolves a provider in this order:

1. `ANTHROPIC_API_KEY` set → Anthropic Messages API (`claude-sonnet-4-6`)
2. `OLLAMA_HOST` set → local Ollama (for air-gapped / sovereign deploys)
3. neither → a deterministic offline analyst grounded in the live feed

Every answer is grounded with the current opportunity feed as context, so the
provider can reference live solicitations, values and incumbents.

## Live ingestion

`POST /api/ingest/find-a-tender` pulls recent OCDS release packages from the
Find a Tender Service, maps them to the opportunity shape and upserts. It
returns `{"upserted": 0}` when the gov.uk endpoint is unreachable (e.g. from an
air-gapped host) — the seed data keeps everything working offline regardless.
Contracts Finder publishes the same OCDS standard and slots in the same way.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/summary` | dashboard metrics |
| GET | `/api/opportunities?q=&market=&vehicle=` | filtered feed |
| GET | `/api/opportunities/{id}` | single solicitation |
| GET | `/api/awards`, `/api/awards/trend` | historical awards + trend |
| GET | `/api/signals` | pre-solicitation intelligence |
| GET | `/api/board` | capture board by stage |
| POST | `/api/board/move` | move a pursuit `{opportunity_id, stage}` |
| DELETE | `/api/board/{id}` | remove a pursuit |
| GET | `/api/workflows`, PATCH `/api/workflows/{id}` | playbooks + toggle |
| POST | `/api/agent` | capture analyst `{question}` |
| POST | `/api/ingest/find-a-tender` | live OCDS ingest |

## Notes

- Data is synthetic; the schema and ingest path are real.
- SQLite by default; set `DATABASE_URL` to a Postgres DSN for production.
- To flip to US federal/SLED (SAM.gov), swap the seed dataset + ingest source —
  the rest is market-agnostic.
