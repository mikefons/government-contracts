# Chancery Intelligence Engine

The predictive layer described in the Opportunity Intelligence concept: start from
**funding and programs**, build a **vendor ontology**, score every program 0–100 for a
given vendor, and answer *"where should we spend the next sales dollar?"* — before an RFP exists.

## What's real and verified
- **Graph model** (`app/intel/graph.py`): property graph with the doc's entities and
  relationship verbs (funds, owns, supports, reports_to, competes, uses, influences).
  Two backends behind one interface: `MemoryGraphStore` (tested) and `ArangoGraphStore`
  (production, AQL traversals). Switch with `GRAPH_BACKEND=memory|arango`.
- **Vendor ontology builder** (`app/intel/ontology.py`): company + capabilities →
  capability map, expanded keywords, mission alignment. Uses Claude when
  `ANTHROPIC_API_KEY` is set; deterministic offline expansion otherwise.
- **Scoring** (`app/intel/scoring.py`): transparent weighted 0–100 model over the doc's
  factors. Returns the per-factor breakdown — never a black box.
- **Queries** (`app/intel/queries.py`): top programs/accounts/expiring contracts, and the
  parameterised multi-hop query (DME threshold, required tech, expiry window, no dominant
  incumbent, min score), ranked.
- **API** (`/api/intel/*`) behind auth/RBAC; **7 engine tests** in `tests/test_intel.py`.

## What is scaffolded, NOT validated (be honest with stakeholders)
- **Federal data is synthetic.** `app/intel/seed_fed.py` is realistic but invented.
- **`ingest_usaspending.py` is written, not run here** — the sandbox can't reach
  api.usaspending.gov. The OCDS/USAspending field mapping needs validating on first
  live contact. IT Dashboard + Congressional Budget Justification loaders are TODOs.
- **ArangoDB adapter is written, not run here** — no Arango server in the build sandbox.
  Logic is verified against the in-memory backend with the identical interface.
- **The score is a heuristic, not a predictive model.** Weights are hand-set priors.
  Making it predictive requires historical won/lost outcomes to backtest and calibrate —
  real ML work, not a constant table. Treat the number as a defensible prioritisation
  signal, not a probability.

## Run with ArangoDB (production graph)
```bash
docker compose --profile arango up --build -d
# set GRAPH_BACKEND=arango and arango creds in .env first
```

## Endpoints
| Method | Path | Role |
|---|---|---|
| POST | /api/intel/vendor | analyst — build ontology from {company, capabilities[], text?} |
| GET  | /api/intel/targets?company= | any — scored programs |
| GET  | /api/intel/accounts?company= | any — scored, aggregated to agency |
| GET  | /api/intel/expiring?months= | any — contracts expiring in window |
| POST | /api/intel/query?company= | any — structured multi-hop filter |
| GET  | /api/intel/weights | any — the scoring weights |
