"""
test_api_timeouts.py — Bounded Timeout Enforcement Tests
"""
from unittest.mock import patch
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


def test_route_calculation_timeout_handling(client):
    """When routing calculation times out, it returns 504 with ROUTE_TIMEOUT JSON."""
    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=TimeoutError("Search exceeded budget")):
        resp = client.post("/api/routes/calculate", json={
            "source_node": "1001",
            "destination_node": "1002",
            "algorithm": "astar",
        })
        assert resp.status_code == 504
        assert resp.is_json
        data = resp.get_json()
        assert data["success"] is False
        assert data["error"] == "ROUTE_TIMEOUT"
        assert "request_id" in data


def test_global_timeout_error_handler(client, app):
    """Direct TimeoutError raised in endpoint triggers 504 JSON error handler."""
    @app.route("/api/test-timeout", methods=["GET"])
    def timeout_endpoint():
        raise TimeoutError("External dependency timeout")

    resp = client.get("/api/test-timeout")
    assert resp.status_code == 504
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "OPERATION_TIMEOUT"
    assert "request_id" in data
