"""
test_external_provider_failure.py — External Traffic Provider Isolation & Graceful Degradation
"""
from unittest.mock import patch
import pytest
from app import create_app
from database.db import db
from app.modules.live_clustering.traffic_provider_service import (
    get_area_traffic,
    traffic_circuit_breaker,
)


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


def test_external_traffic_failure_returns_unavailable_gracefully():
    """When external traffic API raises an exception, the service returns UNAVAILABLE without crashing."""
    traffic_circuit_breaker.reset()
    try:
        with patch("app.modules.live_clustering.traffic_provider_service._fetch_tomtom_flow", side_effect=Exception("TomTom 503 Outage")):
            with patch.dict("os.environ", {"LIVE_TRAFFIC_PROVIDER": "tomtom", "LIVE_TRAFFIC_API_KEY": "fake-key"}):
                res = get_area_traffic(12.9174, 77.6228, 1000)
                assert res["status"] == "UNAVAILABLE"
                assert res["provider"] == "ERROR"
                assert "segments" in res
    finally:
        traffic_circuit_breaker.reset()


def test_circuit_breaker_trips_after_consecutive_failures():
    """Consecutive failures trip the circuit breaker into OPEN state."""
    traffic_circuit_breaker.reset()
    try:
        with patch("app.modules.live_clustering.traffic_provider_service._fetch_tomtom_flow", side_effect=Exception("TomTom 503 Outage")):
            with patch.dict("os.environ", {"LIVE_TRAFFIC_PROVIDER": "tomtom", "LIVE_TRAFFIC_API_KEY": "fake-key"}):
                # Call 3 times to exceed threshold
                for _ in range(3):
                    get_area_traffic(12.9174, 77.6228, 1000)

                assert traffic_circuit_breaker.state == "OPEN"
                assert traffic_circuit_breaker.allow_request() is False
    finally:
        traffic_circuit_breaker.reset()


def test_clustering_traffic_endpoint_does_not_crash_on_provider_outage(client):
    """POST /api/live-clustering/traffic returns clean JSON during external provider outage."""
    traffic_circuit_breaker.reset()
    try:
        with patch("app.modules.live_clustering.traffic_provider_service._fetch_tomtom_flow", side_effect=Exception("Provider down")):
            resp = client.post("/api/live-clustering/traffic", json={
                "latitude": 12.9174,
                "longitude": 77.6228,
                "radius_meters": 1000,
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["traffic"]["status"] == "UNAVAILABLE"
    finally:
        traffic_circuit_breaker.reset()
