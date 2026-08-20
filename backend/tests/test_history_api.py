import pytest
import json
from app import create_app
from database.db import db
from models.user import User
from models.route_history import RouteHistory
from app.modules.auth.security import generate_access_token

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

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email="test@routeflow.com", name="Test")
        user.password_hash = "fakehash"
        db.session.add(user)
        db.session.commit()
        
        # Need to return a detached/re-queried user for use in tests safely
        user_id = user.id
        return db.session.get(User, user_id)

@pytest.fixture
def test_user2(app):
    with app.app_context():
        user = User(email="test2@routeflow.com", name="Test2")
        user.password_hash = "fakehash"
        db.session.add(user)
        db.session.commit()
        return db.session.get(User, user.id)

@pytest.fixture
def auth_headers(app, test_user):
    with app.app_context():
        token = generate_access_token(test_user.id)
        return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers2(app, test_user2):
    with app.app_context():
        token = generate_access_token(test_user2.id)
        return {"Authorization": f"Bearer {token}"}

def test_history_api_unauthorized(client):
    response = client.get('/api/history')
    assert response.status_code == 401

def test_history_api_empty(client, auth_headers):
    response = client.get('/api/history', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 0
    assert data["total"] == 0

def test_history_api_create_and_fetch(client, app, test_user, auth_headers):
    with app.app_context():
        history = RouteHistory(
            user_id=test_user.id,
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

    response = client.get('/api/history', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 1
    assert data["items"][0]["source_name"] == "JP Nagar"
    assert data["items"][0]["destination_name"] == "Whitefield"

def test_history_api_cross_user_isolation(client, app, test_user, auth_headers2):
    with app.app_context():
        history = RouteHistory(
            user_id=test_user.id,
            source_name="Malleswaram",
            destination_name="Indiranagar"
        )
        db.session.add(history)
        db.session.commit()

    # User 2 shouldn't see User 1's history
    response = client.get('/api/history', headers=auth_headers2)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 0

def test_history_api_delete(client, app, test_user, auth_headers):
    with app.app_context():
        history = RouteHistory(
            user_id=test_user.id,
            source_name="Koramangala",
            destination_name="HSR Layout"
        )
        db.session.add(history)
        db.session.commit()
        hist_id = history.id

    response = client.delete(f'/api/history/{hist_id}', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # Check it's gone
    response2 = client.get('/api/history', headers=auth_headers)
    assert len(response2.get_json()["items"]) == 0

def test_history_api_delete_unauthorized(client, app, test_user, auth_headers2):
    with app.app_context():
        history = RouteHistory(
            user_id=test_user.id,
            source_name="Koramangala",
            destination_name="HSR Layout"
        )
        db.session.add(history)
        db.session.commit()
        hist_id = history.id

    # User 2 tries to delete User 1's history
    response = client.delete(f'/api/history/{hist_id}', headers=auth_headers2)
    assert response.status_code == 404

def test_history_api_filters(client, app, test_user, auth_headers):
    with app.app_context():
        h1 = RouteHistory(user_id=test_user.id, source_name="A", algorithm="astar", traffic_level="LOW")
        h2 = RouteHistory(user_id=test_user.id, source_name="B", algorithm="dijkstra", traffic_level="HIGH")
        db.session.add_all([h1, h2])
        db.session.commit()

    res1 = client.get('/api/history?algorithm=astar', headers=auth_headers)
    assert len(res1.get_json()["items"]) == 1

    res2 = client.get('/api/history?traffic_level=HIGH', headers=auth_headers)
    assert len(res2.get_json()["items"]) == 1
    assert res2.get_json()["items"][0]["source_name"] == "B"
