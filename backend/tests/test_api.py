"""API tests: auth, RBAC, audit, board persistence. Uses an isolated temp DB."""
import pytest


def token(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_unauthenticated_is_rejected(client):
    assert client.get("/api/summary").status_code == 401
    assert client.get("/api/opportunities").status_code == 401


def test_admin_login_and_read(client):
    t = token(client, "admin@test.local", "adminpass")
    r = client.get("/api/summary", headers=auth(t))
    assert r.status_code == 200
    assert r.json()["active_pursuits"] >= 1
    assert len(client.get("/api/opportunities", headers=auth(t)).json()) == 10


def test_bad_password(client):
    assert client.post("/api/auth/login", json={"email": "admin@test.local", "password": "nope"}).status_code == 401


def test_rbac_viewer_cannot_mutate(client):
    admin = token(client, "admin@test.local", "adminpass")
    # admin creates a viewer
    r = client.post("/api/users", headers=auth(admin),
                    json={"email": "v@test.local", "password": "viewerpass", "role": "viewer"})
    assert r.status_code == 201
    viewer = token(client, "v@test.local", "viewerpass")
    # viewer can read
    assert client.get("/api/board", headers=auth(viewer)).status_code == 200
    # viewer cannot move
    r = client.post("/api/board/move", headers=auth(viewer),
                    json={"opportunity_id": "OPP-7744", "stage": "Qualify"})
    assert r.status_code == 403


def test_analyst_move_persists_and_audits(client):
    admin = token(client, "admin@test.local", "adminpass")
    r = client.post("/api/board/move", headers=auth(admin),
                    json={"opportunity_id": "OPP-7744", "stage": "Proposal"})
    assert r.status_code == 200
    board = client.get("/api/board", headers=auth(admin)).json()
    assert "OPP-7744" in board["Proposal"]
    # the move is in the audit log
    actions = [e["action"] for e in client.get("/api/audit", headers=auth(admin)).json()]
    assert "board.move" in actions


def test_users_endpoint_requires_admin(client):
    admin = token(client, "admin@test.local", "adminpass")
    client.post("/api/users", headers=auth(admin),
                json={"email": "a@test.local", "password": "analystpass", "role": "analyst"})
    analyst = token(client, "a@test.local", "analystpass")
    r = client.post("/api/users", headers=auth(analyst),
                    json={"email": "x@test.local", "password": "p", "role": "viewer"})
    assert r.status_code == 403
