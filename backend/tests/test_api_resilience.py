"""
test_api_resilience.py — API Resilience, Health & Circuit Breaker Tests
"""
import time
import pytest
from app import create_app
from database.db import db
from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException


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


def test_api_health_endpoint(client):
    """GET /api/health returns 200 with structured component health."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["success"] is True
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "up"
    assert data["dependencies"]["routing_engine"] in ("ready", "initializing", "degraded")
    assert "request_id" in data


def test_circuit_breaker_transitions():
    """Circuit Breaker transitions CLOSED -> OPEN on failures, and recovers to CLOSED."""
    cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitBreaker.STATE_CLOSED
    assert cb.allow_request() is True

    # Record 1st failure (below threshold)
    cb.record_failure(RuntimeError("fail 1"))
    assert cb.state == CircuitBreaker.STATE_CLOSED

    # Record 2nd failure (threshold reached)
    cb.record_failure(RuntimeError("fail 2"))
    assert cb.state == CircuitBreaker.STATE_OPEN
    assert cb.allow_request() is False

    # Calling during OPEN raises CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "should not run")

    # Wait for recovery timeout
    time.sleep(0.12)
    assert cb.allow_request() is True
    assert cb.state == CircuitBreaker.STATE_HALF_OPEN

    # Probe success resets back to CLOSED
    cb.record_success()
    assert cb.state == CircuitBreaker.STATE_CLOSED


def test_health_endpoint_resilient_to_circuit_open(client):
    """External provider circuit breaker in OPEN state must NOT crash /api/health."""
    from app.modules.live_clustering.traffic_provider_service import traffic_circuit_breaker
    try:
        # Trip the circuit breaker
        for _ in range(5):
            traffic_circuit_breaker.record_failure(RuntimeError("simulated provider outage"))
        assert traffic_circuit_breaker.state == CircuitBreaker.STATE_OPEN

        resp = client.get("/api/health")
        # App remains functional (database is up)
        assert resp.status_code in (200, 503)
        data = resp.get_json()
        assert data["dependencies"]["traffic_provider"] == "open"
    finally:
        traffic_circuit_breaker.reset()
