"""
test_concurrent_requests.py — Concurrent Request Handling & Deadlock Prevention
"""
import concurrent.futures
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


def test_concurrent_health_requests(client):
    """Multiple concurrent calls to health endpoint do not deadlock."""
    def _call(i):
        return client.get("/api/health", headers={"X-Request-ID": f"concurrent-{i}"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_call, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for resp in results:
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "healthy"


def test_concurrent_idempotent_writes(client, app):
    """Concurrent identical requests with same Idempotency-Key safely produce at most 1 DB entry."""
    from unittest.mock import patch
    from models.route_history import RouteHistory

    mock_route = {
        "status": "success",
        "algorithm": "astar",
        "distance_km": 8.0,
        "travel_time_seconds": 400,
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [],
        "geometry": [[12.9, 77.5]],
    }

    with patch("app.services.routing_service.routing_service.calculate_route", return_value=mock_route):
        key = "concurrent-idempotency-key-xyz"
        payload = {
            "source_node": "node_x",
            "destination_node": "node_y",
            "algorithm": "astar",
            "source_name": "Concurrent Src",
            "destination_name": "Concurrent Dst",
        }

        def _post():
            return client.post("/api/routes/calculate", json=payload, headers={"Idempotency-Key": key})

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_post) for _ in range(4)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for r in results:
            assert r.status_code == 200

        with app.app_context():
            count = db.session.query(RouteHistory).filter_by(source_name="Concurrent Src").count()
            assert count == 1, f"Expected 1 record, got {count}"
