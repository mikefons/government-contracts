"""Live ingestion from UK OCDS endpoints.

Find a Tender Service (FTS) and Contracts Finder both publish open
OCDS (Open Contracting Data Standard) release packages. This module pulls
recent releases, maps them to Chancery's Opportunity shape, and upserts.

Endpoints (no auth required):
  FTS:              https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages
  Contracts Finder: https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search

Note: these live behind gov.uk domains. In a locked-down/air-gapped
environment the calls will fail and ingest() returns 0 — that is expected;
the seed dataset keeps the app fully functional offline.
"""
from datetime import datetime, date
import httpx
from sqlalchemy.orm import Session
from . import models as m

FTS_URL = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"


def _classify_market(buyer_name: str) -> str:
    n = (buyer_name or "").lower()
    if any(k in n for k in ("council", "nhs", "trust", "university", "college", "police")):
        return "SLED"
    if any(k in n for k in ("commission", "europ", "frontex", "eu ")):
        return "EU"
    return "Federal"


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _map_release(rel: dict) -> dict | None:
    tender = rel.get("tender") or {}
    buyer = (rel.get("buyer") or {}).get("name", "")
    title = tender.get("title") or rel.get("title")
    if not title:
        return None
    val = ((tender.get("value") or {}).get("amount")) or 0
    cpv = ""
    items = tender.get("items") or []
    if items:
        cls = (items[0].get("classification") or {})
        cpv = str(cls.get("id", ""))
    period = tender.get("tenderPeriod") or {}
    return dict(
        id=f"FTS-{rel.get('ocid', rel.get('id',''))}"[:64],
        ref=rel.get("ocid", rel.get("id", ""))[:64],
        title=title[:300],
        agency=buyer or "Unknown buyer",
        market=_classify_market(buyer),
        vehicle="FTS / OJEU",
        cpv=cpv,
        value=int(val),
        close=_parse_date(period.get("endDate")),
        incumbent="None (new requirement)",
        region=(tender.get("deliveryLocation") or {}).get("description", "")[:120] if isinstance(tender.get("deliveryLocation"), dict) else "",
        desc=(tender.get("description") or "")[:2000],
        source="find-a-tender",
    )


def _upsert(db: Session, rows: list[dict]) -> int:
    n = 0
    for row in rows:
        if not row:
            continue
        existing = db.get(m.Opportunity, row["id"])
        if existing:
            for k, v in row.items():
                setattr(existing, k, v)
        else:
            db.add(m.Opportunity(**row))
        n += 1
    db.commit()
    return n


def ingest_find_a_tender(db: Session, limit: int = 50) -> int:
    """Pull recent FTS releases. Returns count upserted. 0 on network failure."""
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(FTS_URL, params={"limit": limit})
            r.raise_for_status()
            pkg = r.json()
    except Exception:
        return 0
    releases = pkg.get("releases", [])
    return _upsert(db, [_map_release(rel) for rel in releases])
