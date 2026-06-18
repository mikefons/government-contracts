"""Intelligence engine API. Mounted under /api/intel.

Stateless across invocations: the seeded federal graph is rebuilt deterministically
per process, and vendor ontologies are persisted in the database (not process memory),
so this works on serverless (Vercel) as well as long-running containers.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ..security import current_user, require_role
from ..database import get_db
from .. import models as m, audit
from .graph import build_store
from .seed_fed import seed_federal
from .ontology import build_ontology
from . import queries as Q
from .scoring import WEIGHTS

router = APIRouter(prefix="/api/intel", tags=["intelligence"])

# Deterministic, read-only seeded graph. Rebuilt per process (fine on cold starts).
_g = build_store()
seed_federal(_g)


def _client_ip(req: Request) -> str:
    return req.client.host if req.client else ""


def _load_ontology(db, company: str | None) -> dict | None:
    if company:
        row = db.get(m.VendorOntology, company.lower())
        if row:
            return row.payload
    row = db.scalars(select(m.VendorOntology).order_by(m.VendorOntology.updated_at.desc()).limit(1)).first()
    return row.payload if row else None


@router.get("/weights")
def scoring_weights(user: m.User = Depends(current_user)):
    return WEIGHTS


@router.post("/vendor")
async def set_vendor(body: dict, request: Request,
                     user: m.User = Depends(require_role("analyst")), db=Depends(get_db)):
    company = (body.get("company") or "Vendor").strip()
    onto = await build_ontology(company, body.get("capabilities") or [], body.get("text") or "")
    row = db.get(m.VendorOntology, company.lower())
    if row:
        row.display_name, row.payload = company, onto
    else:
        db.add(m.VendorOntology(company=company.lower(), display_name=company, payload=onto))
    db.commit()
    audit.record(db, user.email, "intel.vendor.build", target=company,
                 detail={"provider": onto.get("provider")}, ip=_client_ip(request))
    return {"company": company, "ontology": onto}


@router.get("/targets")
def targets(company: str | None = None, limit: int = 50,
            user: m.User = Depends(current_user), db=Depends(get_db)):
    onto = _load_ontology(db, company)
    return {"ontology_loaded": onto is not None, "programs": Q.top_programs(_g, onto, limit)}


@router.get("/accounts")
def accounts(company: str | None = None, limit: int = 50,
             user: m.User = Depends(current_user), db=Depends(get_db)):
    return {"accounts": Q.top_accounts(_g, _load_ontology(db, company), limit)}


@router.get("/expiring")
def expiring(months: int = 24, limit: int = 50, user: m.User = Depends(current_user)):
    return {"contracts": Q.expiring_contracts(_g, months, limit)}


@router.post("/query")
def structured_query(body: dict, company: str | None = None,
                     user: m.User = Depends(current_user), db=Depends(get_db)):
    rows = Q.structured_query(
        _g, _load_ontology(db, company),
        min_dme=int(body.get("min_dme", 0)),
        expiry_months=body.get("expiry_months"),
        require_technologies=body.get("require_technologies"),
        no_dominant_incumbent=bool(body.get("no_dominant_incumbent", False)),
        min_score=float(body.get("min_score", 0)),
        limit=int(body.get("limit", 50)),
    )
    return {"count": len(rows), "programs": rows}
