"""Recommendation queries over the funding graph."""
from datetime import date
from .scoring import score_all


def top_programs(g, ontology, limit=50):
    return score_all(g, ontology)[:limit]


def top_accounts(g, ontology, limit=50):
    """Aggregate program scores up to the owning agency."""
    by_agency: dict[str, list] = {}
    for row in score_all(g, ontology):
        by_agency.setdefault(row["agency"], []).append(row)
    out = []
    for ag, rows in by_agency.items():
        a = g.vertex("agency", ag) or {}
        out.append({
            "agency": ag,
            "name": a.get("name", ag),
            "abbr": a.get("abbr", ""),
            "program_count": len(rows),
            "top_score": max(r["score"] for r in rows),
            "avg_score": round(sum(r["score"] for r in rows) / len(rows), 1),
        })
    out.sort(key=lambda r: r["top_score"], reverse=True)
    return out[:limit]


def expiring_contracts(g, months=24, limit=50):
    horizon = date.today().toordinal() + months * 30
    out = []
    for c in g.vertices("contract"):
        exp = c.get("expires")
        if not exp:
            continue
        d = date.fromisoformat(exp)
        if d.toordinal() <= horizon:
            out.append({"program": c.get("program"), "vendor": c.get("vendor"),
                        "value": c.get("value"), "expires": exp,
                        "days": (d - date.today()).days})
    out.sort(key=lambda r: r["days"])
    return out[:limit]


def structured_query(g, ontology, *, min_dme=0, expiry_months=None,
                     require_technologies=None, no_dominant_incumbent=False,
                     min_score=0, limit=50):
    """The doc's example query, parameterised. Returns ranked programs with breakdown."""
    require_technologies = [t.lower() for t in (require_technologies or [])]
    results = []
    for row in score_all(g, ontology):
        pk = row["program"]
        inv = next((i for i in g.vertices("investment") if i.get("program") == pk), {})
        if inv.get("dme_amount", 0) < min_dme:
            continue
        prog_tech = {n.split("/")[1].replace("_", " ") for n in g.neighbors(f"program/{pk}", "uses")}
        if require_technologies and not all(
            any(req in t for t in prog_tech) for req in require_technologies):
            continue
        contracts = [c for c in g.vertices("contract") if c.get("program") == pk]
        if no_dominant_incumbent and any(c.get("vendor") for c in contracts):
            # treat any single incumbent contract as "dominant" for this demo
            if len(contracts) == 1:
                continue
        if expiry_months is not None:
            soon = any(c.get("expires") and
                       (date.fromisoformat(c["expires"]) - date.today()).days <= expiry_months * 30
                       for c in contracts) or not contracts
            if not soon:
                continue
        if row["score"] < min_score:
            continue
        results.append(row)
    return results[:limit]
