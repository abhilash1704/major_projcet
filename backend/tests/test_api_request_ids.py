"""
test_api_request_ids.py — Request Correlation & X-Request-ID Propagation Tests
"""
import pytest
from app import create_app
from database.db import db


@pytest.fixture
def app():
    app = create_app("test")
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_request_id_injected_when_omitted(client):
    """Endpoints automatically inject a unique X-Request-ID when not supplied by the caller."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    req_id = resp.headers["X-Request-ID"]
    assert req_id.startswith("rf_")

    data = resp.get_json()
    assert data.get("request_id") == req_id


def test_client_request_id_propagated(client):
    """When the client provides X-Request-ID, the backend respects and propagates it."""
    client_id = "client-trace-abc-12345"
    resp = client.get("/api/health", headers={"X-Request-ID": client_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == client_id

    data = resp.get_json()
    assert data.get("request_id") == client_id


def test_unique_request_ids_per_request(client):
    """Subsequent requests generate distinct correlation IDs."""
    resp1 = client.get("/api/health")
    resp2 = client.get("/api/health")
    id1 = resp1.headers.get("X-Request-ID")
    id2 = resp2.headers.get("X-Request-ID")
    assert id1 != id2
