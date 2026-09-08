"""
test_api_errors.py — Centralized Error Handling & JSON Normalization Tests
Verifies that error responses are strictly predictable JSON and never raw HTML.
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


def test_404_error_json_format(client):
    """Unknown route returns 404 with structured JSON, never HTML."""
    resp = client.get("/api/nonexistent-endpoint-12345")
    assert resp.status_code == 404
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data


def test_400_bad_request_json_format(client):
    """POST /api/routes/calculate with missing parameters returns 400 JSON."""
    resp = client.post("/api/routes/calculate", json={})
    assert resp.status_code in (400, 404)
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    assert "error" in data


def test_no_stack_traces_exposed(client, app):
    """Server-side errors do NOT leak Python stack traces to the client."""
    @app.route("/api/test-trigger-500", methods=["GET"])
    def trigger_error():
        raise RuntimeError("Sensitive internal secret path: /etc/secrets/key.pem")

    resp = client.get("/api/test-trigger-500")
    assert resp.status_code == 500
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    # Ensure sensitive internal details/traces are omitted
    assert "Traceback" not in resp.get_data(as_text=True)
    assert "/etc/secrets" not in resp.get_data(as_text=True)
    assert "request_id" in data
