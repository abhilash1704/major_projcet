"""
test_alternative_routes.py — Unit and integration tests for High-Traffic Alternative Route Engine
"""
import pytest
from app import create_app
from app.modules.routing.services.alternative_route_service import alternative_route_service, _compute_route_similarity


@pytest.fixture
def client():
    app = create_app('test')
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_route_similarity_computation():
    path_a = ["n1", "n2", "n3", "n4", "n5"]
    path_b = ["n1", "n2", "n3", "n4", "n5"]
    path_c = ["n1", "n2", "n10", "n11", "n12"]
    
    assert _compute_route_similarity(path_a, path_b) == 1.0
    assert _compute_route_similarity(path_a, path_c) == 0.4
    assert _compute_route_similarity(path_a, []) == 0.0


def test_alternative_route_service_generation(client):
    # Using sample nodes from default graph
    src = "7784026478"
    dst = "1032"

    res = alternative_route_service.generate_alternative_routes(
        source_node=src,
        destination_node=dst,
        traffic_level="HIGH",
        max_alternatives=3,
        request_id="test_req_123"
    )

    assert res is not None
    assert "status" in res
    assert "trigger" in res
    assert res["trigger"] == "HIGH_TRAFFIC"
    assert "current_route" in res
    assert "alternatives" in res
    assert isinstance(res["alternatives"], list)
    assert len(res["alternatives"]) <= 3

    # Check candidates structure if present
    for alt in res["alternatives"]:
        assert "id" in alt
        assert "algorithm" in alt
        assert alt["algorithm"] in ["A_STAR", "DIJKSTRA"]
        assert "distance_km" in alt
        assert "eta_minutes" in alt
        assert "traffic_cost" in alt
        assert "color" in alt
        assert "label" in alt


def test_post_api_routes_alternatives_endpoint(client):
    payload = {
        "source": "7784026478",
        "destination": "1032",
        "traffic_level": "HIGH",
        "max_alternatives": 3,
        "request_id": "api_test_req_456"
    }

    response = client.post('/api/routes/alternatives', json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert data is not None
    assert data.get("status") in ["success", "partial"]
    assert data.get("trigger") == "HIGH_TRAFFIC"
    assert "current_route" in data
    assert "alternatives" in data
