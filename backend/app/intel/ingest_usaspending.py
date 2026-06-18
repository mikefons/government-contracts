"""USAspending ingestion (production code; NOT run in this build — network locked).

USAspending publishes an open POST API. This maps awards into the funding graph as
contract + vendor vertices linked to programs. The IT Dashboard and Congressional
Budget Justification loaders follow the same pattern and are left as TODOs.

Reference: https://api.usaspending.gov/api/v2/search/spending_by_award/
"""
import httpx

USASPENDING = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def ingest_usaspending(g, naics=None, limit=100) -> int:
    """Pull recent awards and attach them to the graph. Returns count. 0 on failure."""
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "naics_codes": naics or ["541512"],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount",
                   "Awarding Agency", "End Date", "Description"],
        "limit": limit,
        "page": 1,
    }
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(USASPENDING, json=payload)
            r.raise_for_status()
            rows = r.json().get("results", [])
    except Exception:
        return 0

    n = 0
    for row in rows:
        award_id = str(row.get("Award ID") or "").strip()
        vendor = (row.get("Recipient Name") or "Unknown").strip()
        if not award_id:
            continue
        vk = vendor.lower().replace(" ", "_")[:60]
        if not g.vertex("vendor", vk):
            g.add_vertex("vendor", vk, name=vendor)
        g.add_vertex("contract", f"usa_{award_id}"[:60],
                     vendor=vk, value=int(row.get("Award Amount") or 0),
                     expires=row.get("End Date"),
                     description=(row.get("Description") or "")[:500])
        n += 1
    return n
