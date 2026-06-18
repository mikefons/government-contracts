"""Opportunity scoring.

Transparent, vendor-specific weighted model producing a 0-100 score per program.
Inputs follow the concept doc. Each factor is normalised to 0..1, weighted, summed.

IMPORTANT (honesty): this is a defensible *heuristic*, not a validated predictive
model. The weights are hand-set priors. Turning this into something predictive needs
historical won/lost outcomes to backtest and calibrate against — that is real ML work,
not a constant table. The breakdown is returned so the number is never a black box.
"""
from datetime import date

WEIGHTS = {
    "funding": 0.16,
    "dme_growth": 0.12,
    "modernization": 0.12,
    "contract_expiration": 0.14,
    "hiring_growth": 0.06,
    "technology_alignment": 0.20,
    "competitive_position": 0.12,
    "mission_relevance": 0.08,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def _norm_funding(dme: float) -> float:
    # £0 -> 0, $50M+ -> 1 (log-ish via cap)
    return max(0.0, min(1.0, dme / 50_000_000))


def _norm_expiry(expires_iso: str | None) -> float:
    # No incumbent contract -> open field (1.0). Sooner expiry -> higher (displaceable).
    if not expires_iso:
        return 1.0
    days = (date.fromisoformat(expires_iso) - date.today()).days
    if days <= 0:
        return 1.0
    if days >= 730:  # >24 months out: low near-term opportunity
        return 0.15
    return 1.0 - (days / 730) * 0.85


def score_program(g, program_key: str, ontology: dict | None) -> dict:
    """Return {score, factors:{...}} for one program against a vendor ontology."""
    inv = next((i for i in g.vertices("investment") if i.get("program") == program_key), None)
    prog = g.vertex("program", program_key)
    if not prog:
        return {"score": 0, "factors": {}}

    dme = (inv or {}).get("dme_amount", 0)
    f = {
        "funding": _norm_funding(dme),
        "dme_growth": max(0.0, min(1.0, (inv or {}).get("dme_growth", 0) / 0.35)),
        "modernization": (inv or {}).get("modernization", 0),
        "hiring_growth": max(0.0, min(1.0, (inv or {}).get("hiring_growth", 0) / 0.25)),
    }

    # contract expiration: best (soonest/none) across this program's contracts
    contracts = [c for c in g.vertices("contract") if c.get("program") == program_key]
    f["contract_expiration"] = max([_norm_expiry(c.get("expires")) for c in contracts], default=1.0)

    # competitive position: no incumbent -> 1.0; one strong incumbent -> lower
    incumbents = {c.get("vendor") for c in contracts if c.get("vendor")}
    f["competitive_position"] = 1.0 if not incumbents else 0.45

    # technology alignment: overlap of program tech with vendor ontology keywords
    prog_tech = {n.split("/")[1].replace("_", " ") for n in g.neighbors(f"program/{program_key}", "uses")}
    vocab = set()
    if ontology:
        vocab |= {k.lower() for k in ontology.get("expanded_keywords", [])}
        vocab |= {c.lower() for c in ontology.get("capability_map", [])}
    overlap = len(prog_tech & vocab)
    f["technology_alignment"] = min(1.0, overlap / 3.0) if vocab else 0.4

    # mission relevance: program mission priority (1..5) scaled, lifted by ontology mission match
    mission_ids = [m.split("/")[1] for m in g.neighbors(f"program/{program_key}", "influences", direction="in")]
    pr = max([(g.vertex("mission", mid) or {}).get("priority", 3) for mid in mission_ids], default=3)
    base = pr / 5.0
    if ontology:
        aligned = {a.get("mission") for a in ontology.get("mission_alignment", [])}
        if set(mission_ids) & aligned:
            base = min(1.0, base + 0.2)
    f["mission_relevance"] = base

    score = round(100 * sum(WEIGHTS[k] * f.get(k, 0) for k in WEIGHTS), 1)
    return {"score": score, "factors": {k: round(v, 3) for k, v in f.items()}}


def score_all(g, ontology: dict | None) -> list[dict]:
    rows = []
    for p in g.vertices("program"):
        s = score_program(g, p["_key"], ontology)
        incumbents = [c.get("vendor") for c in g.vertices("contract") if c.get("program") == p["_key"]]
        rows.append({
            "program": p["_key"],
            "name": p.get("name"),
            "agency": p.get("agency"),
            "peo": p.get("peo"),
            "score": s["score"],
            "factors": s["factors"],
            "incumbent": (incumbents[0] if incumbents and incumbents[0] else None),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows
