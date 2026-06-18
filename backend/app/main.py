"""Chancery API — FastAPI application (production-hardened).

Run:  uvicorn app.main:app --port 8000
Docs: http://localhost:8000/docs
"""
from datetime import date, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db, engine, Base
from . import models as m, schemas as s, agent as agent_mod, audit
from .ingest import ingest_find_a_tender
from .seed import seed, bootstrap_admin
from .security import (
    current_user, require_role, verify_password, create_access_token, hash_password,
)
from .logging_mw import configure_logging, RequestContextMiddleware, RateLimitMiddleware, logger

STAGES = ["Identify", "Qualify", "Capture", "Proposal", "Submitted"]


_initialized = False


def ensure_initialized():
    """Idempotent startup work. Safe to call from lifespan (containers) or on the
    first request (serverless, where lifespan may not run)."""
    global _initialized
    if _initialized:
        return
    configure_logging()
    if settings.run_create_all:
        Base.metadata.create_all(bind=engine)
    seed()
    if bootstrap_admin():
        logger.info("bootstrapped admin user %s", settings.admin_email)
    _initialized = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_initialized()
    scheduler = None
    if settings.enable_scheduler and not settings.serverless:
        from .scheduler import start_scheduler
        scheduler = start_scheduler()
        logger.info("ingest scheduler started (%s min)", settings.ingest_interval_minutes)
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Chancery API", version="2.1.0", lifespan=lifespan)


@app.middleware("http")
async def _init_guard(request: Request, call_next):
    # Serverless safety net: lifespan isn't guaranteed to run on Vercel.
    if not _initialized:
        ensure_initialized()
    return await call_next(request)


if settings.enable_rate_limit and not settings.serverless:
    app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .intel.api import router as intel_router  # noqa: E402
app.include_router(intel_router)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


# ── Health / readiness ─────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ready"}


# ── Auth ───────────────────────────────────────────────────────────────
@app.post("/api/auth/login", response_model=s.Token)
def login(body: s.LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(m.User).where(m.User.email == body.email))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        audit.record(db, body.email, "auth.login.fail", ip=client_ip(request))
        raise HTTPException(401, "Incorrect email or password")
    audit.record(db, user.email, "auth.login.ok", ip=client_ip(request))
    return s.Token(access_token=create_access_token(user.email, user.role),
                   role=user.role, name=user.name)


@app.get("/api/auth/me", response_model=s.UserOut)
def me(user: m.User = Depends(current_user)):
    return user


@app.post("/api/users", response_model=s.UserOut, status_code=201)
def create_user(body: s.UserCreate, request: Request,
                admin: m.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "Invalid role")
    if db.scalar(select(m.User).where(m.User.email == body.email)):
        raise HTTPException(409, "Email already exists")
    u = m.User(email=body.email, name=body.name, role=body.role,
               password_hash=hash_password(body.password))
    db.add(u); db.commit(); db.refresh(u)
    audit.record(db, admin.email, "user.create", target=body.email,
                 detail={"role": body.role}, ip=client_ip(request))
    return u


# ── Opportunities (read: any authenticated user) ───────────────────────
@app.get("/api/opportunities", response_model=list[s.OpportunityOut])
def list_opportunities(q: str | None = None, market: str | None = None, vehicle: str | None = None,
                       user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(m.Opportunity)
    if market and market != "All":
        stmt = stmt.where(m.Opportunity.market == market)
    if vehicle and vehicle != "All":
        stmt = stmt.where(m.Opportunity.vehicle == vehicle)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(
            func.lower(m.Opportunity.title).like(like),
            func.lower(m.Opportunity.agency).like(like),
            func.lower(m.Opportunity.ref).like(like),
            func.lower(m.Opportunity.incumbent).like(like),
        ))
    stmt = stmt.order_by(m.Opportunity.close.is_(None), m.Opportunity.close)
    return db.scalars(stmt).all()


@app.get("/api/opportunities/{opp_id}", response_model=s.OpportunityOut)
def get_opportunity(opp_id: str, user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    o = db.get(m.Opportunity, opp_id)
    if not o:
        raise HTTPException(404, "Opportunity not found")
    return o


# ── Awards / signals (read) ────────────────────────────────────────────
@app.get("/api/awards", response_model=list[s.AwardOut])
def list_awards(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(m.Award).order_by(m.Award.date.desc())).all()


@app.get("/api/awards/trend")
def award_trend(user: m.User = Depends(current_user)):
    return [{"q": q, "v": v} for q, v in
            [("Q3'24",62),("Q4'24",78),("Q1'25",71),("Q2'25",94),
             ("Q3'25",88),("Q4'25",121),("Q1'26",134),("Q2'26",152)]]


@app.get("/api/signals", response_model=list[s.SignalOut])
def list_signals(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(m.Signal).order_by(m.Signal.score.desc())).all()


# ── Capture board (read any; write requires analyst+) ──────────────────
@app.get("/api/board")
def get_board(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    board = {st: [] for st in STAGES}
    for p in db.scalars(select(m.Pursuit).order_by(m.Pursuit.position)).all():
        board.setdefault(p.stage, []).append(p.opportunity_id)
    return board


@app.post("/api/board/move", response_model=s.PursuitOut)
def move_pursuit(req: s.MoveRequest, request: Request,
                 user: m.User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    if req.stage not in STAGES:
        raise HTTPException(400, f"Unknown stage '{req.stage}'")
    if not db.get(m.Opportunity, req.opportunity_id):
        raise HTTPException(404, "Opportunity not found")
    p = db.get(m.Pursuit, req.opportunity_id)
    max_pos = db.scalar(select(func.count()).select_from(m.Pursuit).where(m.Pursuit.stage == req.stage)) or 0
    if p:
        p.stage = req.stage; p.position = max_pos
    else:
        p = m.Pursuit(opportunity_id=req.opportunity_id, stage=req.stage, position=max_pos)
        db.add(p)
    db.commit(); db.refresh(p)
    audit.record(db, user.email, "board.move", target=req.opportunity_id,
                 detail={"stage": req.stage}, ip=client_ip(request))
    return p


@app.delete("/api/board/{opp_id}", status_code=204)
def remove_pursuit(opp_id: str, request: Request,
                   user: m.User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    p = db.get(m.Pursuit, opp_id)
    if p:
        db.delete(p); db.commit()
        audit.record(db, user.email, "board.remove", target=opp_id, ip=client_ip(request))


# ── Workflows (read any; toggle requires analyst+) ─────────────────────
@app.get("/api/workflows", response_model=list[s.WorkflowOut])
def list_workflows(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(m.Workflow).order_by(m.Workflow.id)).all()


@app.patch("/api/workflows/{wf_id}", response_model=s.WorkflowOut)
def toggle_workflow(wf_id: int, body: s.WorkflowToggle, request: Request,
                    user: m.User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    wf = db.get(m.Workflow, wf_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    wf.enabled = body.enabled
    db.commit(); db.refresh(wf)
    audit.record(db, user.email, "workflow.toggle", target=str(wf_id),
                 detail={"enabled": body.enabled}, ip=client_ip(request))
    return wf


# ── Agent ──────────────────────────────────────────────────────────────
@app.post("/api/agent", response_model=s.AgentResponse)
async def agent_endpoint(req: s.AgentRequest, request: Request,
                         user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    if not (req.question or "").strip():
        raise HTTPException(400, "Empty question")
    opps = db.scalars(select(m.Opportunity)).all()
    answer, provider = await agent_mod.ask(req.question[:2000], opps)
    audit.record(db, user.email, "agent.query", detail={"provider": provider}, ip=client_ip(request))
    return s.AgentResponse(answer=answer, provider=provider)


# ── Ingestion (admin only) ─────────────────────────────────────────────
@app.post("/api/ingest/find-a-tender")
def trigger_ingest(request: Request, limit: int = Query(50, le=200),
                   admin: m.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    n = ingest_find_a_tender(db, limit=limit)
    audit.record(db, admin.email, "ingest.find-a-tender", detail={"upserted": n}, ip=client_ip(request))
    return {"upserted": n, "source": "find-a-tender",
            "note": "0 means the gov.uk endpoint was unreachable from this host (e.g. air-gapped)."}


# ── Audit log (admin only) ─────────────────────────────────────────────
@app.get("/api/audit", response_model=list[s.AuditOut])
def list_audit(limit: int = Query(100, le=500),
               admin: m.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(m.AuditLog).order_by(m.AuditLog.ts.desc()).limit(limit)).all()


# ── Dashboard summary ──────────────────────────────────────────────────
@app.get("/api/summary", response_model=s.Summary)
def summary(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    pursuit_ids = db.scalars(select(m.Pursuit.opportunity_id)).all()
    pipeline = db.scalar(select(func.coalesce(func.sum(m.Opportunity.value), 0))
                         .where(m.Opportunity.id.in_(pursuit_ids))) or 0
    week = date.today() + timedelta(days=7)
    closing = db.scalar(select(func.count()).select_from(m.Opportunity)
                        .where(m.Opportunity.close.is_not(None),
                               m.Opportunity.close <= week, m.Opportunity.close >= date.today())) or 0
    sig_total = db.scalar(select(func.count()).select_from(m.Signal)) or 0
    sig_high = db.scalar(select(func.count()).select_from(m.Signal).where(m.Signal.score >= 80)) or 0
    return s.Summary(pipeline_value=int(pipeline), active_pursuits=len(pursuit_ids),
                     closing_this_week=int(closing), signals=int(sig_total), high_signals=int(sig_high))
