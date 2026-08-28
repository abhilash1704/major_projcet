import pytest
import json
from app import create_app
from database.db import db
from models.route_history import RouteHistory

@pytest.fixture
def app():
    app = create_app('test')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_history_api_empty(client):
    response = client.get('/api/history')
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 0
    assert data["total"] == 0

def test_history_api_create_and_fetch(client, app):
    with app.app_context():
        history = RouteHistory(
            user_id="guest_user",
            source_name="JP Nagar",
            destination_name="Whitefield",
            distance_km=15.5,
            eta_minutes=45,
            algorithm="astar",
            routing_mode="normal",
            traffic_level="MEDIUM"
        )
        db.session.add(history)
        db.session.commit()

    response = client.get('/api/history')
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 1
    assert data["items"][0]["source_name"] == "JP Nagar"
    assert data["items"][0]["destination_name"] == "Whitefield"

def test_history_api_delete(client, app):
    with app.app_context():
        history = RouteHistory(
            user_id="guest_user",
            source_name="Koramangala",
            destination_name="HSR Layout"
        )
        db.session.add(history)
        db.session.commit()
        hist_id = history.id

    response = client.delete(f'/api/history/{hist_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # Check it's gone
    response2 = client.get('/api/history')
    assert len(response2.get_json()["items"]) == 0

def test_history_api_filters(client, app):
    with app.app_context():
        h1 = RouteHistory(user_id="guest_user", source_name="A", algorithm="astar", traffic_level="LOW")
        h2 = RouteHistory(user_id="guest_user", source_name="B", algorithm="dijkstra", traffic_level="HIGH")
        db.session.add_all([h1, h2])
        db.session.commit()

    res1 = client.get('/api/history?algorithm=astar')
    assert len(res1.get_json()["items"]) == 1

    res2 = client.get('/api/history?traffic_level=HIGH')
    assert len(res2.get_json()["items"]) == 1
    assert res2.get_json()["items"][0]["source_name"] == "B"
