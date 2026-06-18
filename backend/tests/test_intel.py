"""Intelligence engine tests: graph, ontology, scoring, queries, and API routes."""
import asyncio
from app.intel.graph import MemoryGraphStore
from app.intel.seed_fed import seed_federal
from app.intel.ontology import build_ontology
from app.intel import queries as Q, scoring


def fresh():
    g = MemoryGraphStore(); seed_federal(g); return g


def onto():
    return asyncio.new_event_loop().run_until_complete(
        build_ontology("ArangoDB", ["graph database", "knowledge graph", "entity resolution",
                                    "data fabric", "rag", "link analysis"]))


def test_graph_seeded():
    g = fresh()
    assert len(g.vertices("program")) == 10
    assert len(g.vertices("agency")) == 5
    assert g.neighbors("program/jadc2_data", "uses")  # has technologies


def test_ontology_offline_expands_and_aligns():
    o = onto()
    assert o["provider"] == "offline"
    assert "graph analytics" in o["expanded_keywords"]
    assert any(a["mission"] == "fin_crime" for a in o["mission_alignment"])


def test_scores_bounded_and_ranked():
    g, o = fresh(), onto()
    rows = Q.top_programs(g, o, 50)
    assert all(0 <= r["score"] <= 100 for r in rows)
    assert rows == sorted(rows, key=lambda r: r["score"], reverse=True)
    # an open, high-funding, well-aligned program should beat a low one
    top = rows[0]
    assert top["score"] > rows[-1]["score"]


def test_alignment_changes_score():
    g = fresh()
    aligned = scoring.score_program(g, "sanctions_graph", onto())["score"]
    none = scoring.score_program(g, "sanctions_graph", None)["score"]
    assert aligned != none  # vendor ontology actually moves the number


def test_structured_query_filters():
    g, o = fresh(), onto()
    rows = Q.structured_query(g, o, min_dme=10_000_000,
                              require_technologies=["graph", "entity"],
                              expiry_months=24, no_dominant_incumbent=True)
    assert all(r["score"] > 0 for r in rows)
    # every result must actually use a graph technology
    for r in rows:
        techs = {n.split("/")[1] for n in g.neighbors(f"program/{r['program']}", "uses")}
        assert any("graph" in t or "entity" in t for t in techs)


def test_expiring_contracts_sorted():
    g = fresh()
    exp = Q.expiring_contracts(g, months=24)
    assert exp == sorted(exp, key=lambda r: r["days"])


# ── API routes (use shared client fixture) ──
def test_intel_api_flow(client):
    h = lambda t: {"Authorization": f"Bearer {t}"}
    tok = client.post("/api/auth/login",
                      json={"email": "admin@test.local", "password": "adminpass"}).json()["access_token"]
    assert client.get("/api/intel/targets").status_code == 401  # auth required
    r = client.post("/api/intel/vendor", headers=h(tok),
                    json={"company": "ArangoDB",
                          "capabilities": ["graph database", "entity resolution", "knowledge graph"]})
    assert r.status_code == 200
    assert r.json()["ontology"]["expanded_keywords"]
    t = client.get("/api/intel/targets?company=ArangoDB", headers=h(tok)).json()
    assert t["ontology_loaded"] is True
    assert len(t["programs"]) == 10
    q = client.post("/api/intel/query?company=ArangoDB", headers=h(tok),
                    json={"min_dme": 10000000, "require_technologies": ["graph"], "no_dominant_incumbent": True})
    assert q.status_code == 200 and q.json()["count"] >= 1
