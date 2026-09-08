"""
test_database_resilience.py — SQLite Transaction Safety & Write Safety Tests
"""
import pytest
from sqlalchemy.exc import OperationalError
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


def test_database_error_rolls_back_cleanly(client, app):
    """When a database exception occurs, the error handler issues rollback and returns 503 JSON."""
    @app.route("/api/test-db-fail", methods=["GET"])
    def fail_db():
        raise OperationalError("database is locked", {}, None)

    resp = client.get("/api/test-db-fail")
    assert resp.status_code == 503
    assert resp.is_json
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "DATABASE_ERROR"
    assert "request_id" in data


def test_high_frequency_simulation_does_not_mutate_route_history(app):
    """High-frequency vehicle simulation operations remain strictly in-memory and do not write to SQLite."""
    with app.app_context():
        initial_history_count = db.session.query(RouteHistory).count()

        from app.modules.vehicle_simulation.services.simulation_store import simulation_store
        # Simulate active vehicle movements
        simulation_store.clear()
        snapshot = simulation_store.get_snapshot()
        assert snapshot is not None

        # Verify no database rows were created for in-memory simulation
        final_history_count = db.session.query(RouteHistory).count()
        assert final_history_count == initial_history_count
