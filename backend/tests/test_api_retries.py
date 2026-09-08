"""
test_api_retries.py — Retry Policy & Idempotency Tests
Verifies that duplicate requests with the same Idempotency-Key do not create duplicate records.
"""
from unittest.mock import patch
import pytest
from app import create_app
from database.db import db
from models.route_history import RouteHistory


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


def test_idempotent_route_calculate_prevents_duplicate_history(client, app):
    """Retrying route calculate with the same Idempotency-Key does NOT create duplicate RouteHistory rows."""
    mock_route = {
        "status": "success",
        "algorithm": "astar",
        "distance_km": 5.0,
        "travel_time_seconds": 300,
        "nodes": [{"id": "s"}, {"id": "d"}],
        "edges": [],
        "geometry": [[12.9, 77.5]],
    }

    with patch("app.services.routing_service.routing_service.calculate_route", return_value=mock_route):
        headers = {"Idempotency-Key": "retry-key-uuid-1234"}
        payload = {
            "source_node": "src_1",
            "destination_node": "dst_1",
            "algorithm": "astar",
            "source_name": "Location A",
            "destination_name": "Location B",
        }

        # Attempt 1
        resp1 = client.post("/api/routes/calculate", json=payload, headers=headers)
        assert resp1.status_code == 200

        # Attempt 2 (Retry of transient network drop)
        resp2 = client.post("/api/routes/calculate", json=payload, headers=headers)
        assert resp2.status_code == 200

        # Verify only 1 record was written to the database
        with app.app_context():
            count = db.session.query(RouteHistory).filter_by(source_name="Location A").count()
            assert count == 1, f"Expected exactly 1 RouteHistory record, got {count}"


def test_429_rate_limit_response_shape(client, app):
    """429 Too Many Requests returns standard rate limit JSON."""
    from werkzeug.exceptions import TooManyRequests

    @app.route("/api/test-429", methods=["GET"])
    def trigger_429():
        raise TooManyRequests()

    resp = client.get("/api/test-429")
    assert resp.status_code == 429
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "TOO_MANY_REQUESTS"
    assert "request_id" in data
