# Chancery — Deployment

Production-hardened build. **Auth, RBAC, audit log, Postgres + Alembic migrations,
tests, structured logging, rate limiting, security headers, non-root container.**

## 1. Configure secrets

```bash
cd chancery
cp .env.example .env
# generate a real signing key
sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env   # macOS
# set POSTGRES_PASSWORD and a strong ADMIN_PASSWORD in .env as well
```

## 2. Run (Postgres + migrate-on-start)

```bash
docker compose up --build -d
docker compose ps
```

On boot the backend runs `alembic upgrade head`, then seeds reference data and the
admin user from `.env`. App → http://localhost:8080 · API → :8000 · docs → :8000/docs

## 3. First login

Sign in at http://localhost:8080 with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
Create further users (admin only):

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@chancery.local","password":"YOUR_ADMIN_PASSWORD"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST localhost:8000/api/users -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@chancery.local","name":"Capture Lead","password":"change-me","role":"analyst"}'
```

Roles: `viewer` (read only) · `analyst` (read + board/workflow writes) · `admin` (+ users, ingest, audit).

## 4. Tests

```bash
cd backend && pip install -r requirements.txt && python -m pytest -q
```

## 5. Migrations (when you change models)

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## What's hardened
- JWT auth (bcrypt hashing), RBAC on every mutating route
- Append-only audit log; `GET /api/audit` (admin)
- Postgres with Alembic migrations (SQLite still works for local dev)
- Per-IP rate limiting, request IDs, JSON structured logs
- nginx security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy)
- Non-root container, healthcheck, readiness probe (`/api/ready`)
- 7-test pytest suite (auth, RBAC denial, audit, persistence)

## Still yours before going live (cannot be done blind)
- **TLS**: terminate HTTPS at a load balancer / reverse proxy and set your domain in `CORS_ORIGINS`.
- **Real data**: validate `ingest.py` against a live Find a Tender OCDS payload; the field mapping will likely need tuning on first contact.
- **Rotate the bootstrap admin** immediately; consider SSO/OIDC for real users.
- **Secrets manager** (not `.env`) for SECRET_KEY / DB creds in production.
- **Security review / pen test** and, for OFFICIAL-SENSITIVE buyers, formal assurance.
- **Backups** for the Postgres volume; move rate-limit state to Redis if you run >1 backend instance.
