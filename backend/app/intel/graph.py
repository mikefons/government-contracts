"""Graph system of record.

A small property-graph abstraction with two backends:
  - MemoryGraphStore  : pure-Python, used for tests and offline/dev. Fully exercised.
  - ArangoGraphStore  : python-arango adapter for production. Real code, but NOT run
                        in this build (no ArangoDB server in the sandbox).

The intelligence engine (scoring, queries, ontology load) talks only to GraphStore,
so the backend is swappable via GRAPH_BACKEND=memory|arango.

Vertex collections: agency, program, investment, contract, vendor, technology, mission, person
Edge collections (the doc's relationship verbs):
  funds, owns, supports, reports_to, competes, uses, influences
(contract expiry is a property on `contract`, not an edge.)
"""
from __future__ import annotations
from typing import Protocol, Iterable


VERTEX_COLLECTIONS = ["agency", "program", "investment", "contract", "vendor", "technology", "mission", "person"]
EDGE_COLLECTIONS = ["funds", "owns", "supports", "reports_to", "competes", "uses", "influences"]


class GraphStore(Protocol):
    def add_vertex(self, collection: str, key: str, **props) -> None: ...
    def add_edge(self, collection: str, _from: str, _to: str, **props) -> None: ...
    def vertex(self, collection: str, key: str) -> dict | None: ...
    def vertices(self, collection: str) -> list[dict]: ...
    def edges(self, collection: str) -> list[dict]: ...
    def neighbors(self, vertex_id: str, edge_collection: str, direction: str = "out") -> list[str]: ...


class MemoryGraphStore:
    """In-memory property graph. Vertex ids are 'collection/key'."""
    def __init__(self):
        self.v: dict[str, dict[str, dict]] = {c: {} for c in VERTEX_COLLECTIONS}
        self.e: dict[str, list[dict]] = {c: [] for c in EDGE_COLLECTIONS}

    def add_vertex(self, collection: str, key: str, **props) -> None:
        self.v[collection][key] = {"_id": f"{collection}/{key}", "_key": key, **props}

    def add_edge(self, collection: str, _from: str, _to: str, **props) -> None:
        self.e[collection].append({"_from": _from, "_to": _to, **props})

    def vertex(self, collection: str, key: str) -> dict | None:
        return self.v[collection].get(key)

    def vertices(self, collection: str) -> list[dict]:
        return list(self.v[collection].values())

    def edges(self, collection: str) -> list[dict]:
        return list(self.e[collection])

    def neighbors(self, vertex_id: str, edge_collection: str, direction: str = "out") -> list[str]:
        out = []
        for e in self.e[edge_collection]:
            if direction == "out" and e["_from"] == vertex_id:
                out.append(e["_to"])
            elif direction == "in" and e["_to"] == vertex_id:
                out.append(e["_from"])
            elif direction == "any" and vertex_id in (e["_from"], e["_to"]):
                out.append(e["_to"] if e["_from"] == vertex_id else e["_from"])
        return out


class ArangoGraphStore:
    """Production adapter (python-arango). Written for deployment; not run in this build.

    Pushes traversals to AQL for performance; the primitive interface matches
    MemoryGraphStore so the engine code is identical across backends.
    """
    def __init__(self, url: str, db: str, username: str, password: str):
        from arango import ArangoClient  # imported lazily so dev/test never needs the driver
        self.client = ArangoClient(hosts=url)
        sys_db = self.client.db("_system", username=username, password=password)
        if not sys_db.has_database(db):
            sys_db.create_database(db)
        self.db = self.client.db(db, username=username, password=password)
        for c in VERTEX_COLLECTIONS:
            if not self.db.has_collection(c):
                self.db.create_collection(c)
        for c in EDGE_COLLECTIONS:
            if not self.db.has_collection(c):
                self.db.create_collection(c, edge=True)

    def add_vertex(self, collection: str, key: str, **props) -> None:
        self.db.collection(collection).insert({"_key": key, **props}, overwrite=True)

    def add_edge(self, collection: str, _from: str, _to: str, **props) -> None:
        self.db.collection(collection).insert({"_from": _from, "_to": _to, **props})

    def vertex(self, collection: str, key: str) -> dict | None:
        return self.db.collection(collection).get(key)

    def vertices(self, collection: str) -> list[dict]:
        return list(self.db.collection(collection).all())

    def edges(self, collection: str) -> list[dict]:
        return list(self.db.collection(collection).all())

    def neighbors(self, vertex_id: str, edge_collection: str, direction: str = "out") -> list[str]:
        d = {"out": "OUTBOUND", "in": "INBOUND", "any": "ANY"}[direction]
        cur = self.db.aql.execute(
            f"FOR v IN 1..1 {d} @start {edge_collection} RETURN v._id",
            bind_vars={"start": vertex_id},
        )
        return list(cur)


def build_store():
    """Factory honouring GRAPH_BACKEND. Defaults to memory."""
    from ..config import settings
    if settings.graph_backend == "arango":
        return ArangoGraphStore(settings.arango_url, settings.arango_db,
                                settings.arango_user, settings.arango_password)
    return MemoryGraphStore()
