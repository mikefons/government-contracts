"""Shared test setup. Env is configured before the app is imported anywhere."""
import os
import tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "adminpass"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    return client.post("/api/auth/login",
                       json={"email": "admin@test.local", "password": "adminpass"}).json()["access_token"]


def pytest_sessionfinish(session, exitstatus):
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
