"""
Unit test suite for Sprint 9B — Traffic-Aware A* and Dijkstra Integration
"""
import pytest
import networkx as nx
from flask import Flask

from app.services.routing_service import RoutingService
from app.modules.traffic_intelligence.services.traffic_cost_service import TrafficCostService, traffic_cost_service
from app.modules.road_network.services.graph_service import graph_service


@pytest.fixture(autouse=True)
def clear_cache():
    import app.modules.vehicle_simulation.services.route_store as route_store
    route_store.clear_route()
    from app.services.routing_service import routing_service
    routing_service.clear_route_cache()
    yield
    route_store.clear_route()
    routing_service.clear_route_cache()


@pytest.fixture
def test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["TRAFFIC_PENALTY_FACTOR_LOW"] = 1.15
    app.config["TRAFFIC_PENALTY_FACTOR_MEDIUM"] = 1.60
    app.config["TRAFFIC_PENALTY_FACTOR_HIGH"] = 3.00
    return app


@pytest.fixture
def mock_graph():
    """
    Creates a simple diamond graph for testing traffic bypass:
    0 -> 1 (short, 10s) -> 3
    0 -> 2 (longer, 12s) -> 3
    """
    G = nx.MultiDiGraph()
    G.add_node("0", lat=12.9716, lon=77.5946)
    G.add_node("1", lat=12.9720, lon=77.5950)
    G.add_node("2", lat=12.9710, lon=77.5960)
    G.add_node("3", lat=12.9730, lon=77.5970)

    # Edge 0-1: 500m, 10s
    G.add_edge("0", "1", key=0, length=500.0, travel_time=10.0)
    # Edge 1-3: 500m, 10s
    G.add_edge("1", "3", key=0, length=500.0, travel_time=10.0)

    # Edge 0-2: 600m, 12s
    G.add_edge("0", "2", key=0, length=600.0, travel_time=12.0)
    # Edge 2-3: 600m, 12s
    G.add_edge("2", "3", key=0, length=600.0, travel_time=12.0)

    return G


def test_routing_mode_defaults(test_app, monkeypatch, mock_graph):
    """Verify default routing mode is 'normal' and returns standard travel time."""
    service = RoutingService()

    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)

    with test_app.app_context():
        res_normal = service.calculate_route("0", "3", algorithm="astar", routing_mode="normal")
        assert res_normal["routing_mode"] == "normal"
        assert res_normal["nodes"] == [{"id": "0", "lat": 12.9716, "lon": 77.5946}, {"id": "1", "lat": 12.9720, "lon": 77.5950}, {"id": "3", "lat": 12.9730, "lon": 77.5970}]
        assert res_normal["total_travel_time_seconds"] == 20.0
        assert res_normal["traffic_cost"] == 0.0


def test_traffic_aware_bypass(test_app, monkeypatch, mock_graph):
    """
    Test that high traffic on the shorter path (0->1->3) forces traffic-aware routing
    to choose the longer path (0->2->3) when cost is lower.
    """
    service = RoutingService()

    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)

    # Mock high traffic penalty factor 3.0 on 0-1 and 1-3 (cost becomes 30s + 30s = 60s)
    mock_traffic_costs = {
        "success": True,
        "version": 42,
        "edge_costs": [
            {
                "edge_id": "0-1-0",
                "source_node": "0",
                "target_node": "1",
                "traffic_level": "HIGH",
                "penalty_factor": 3.0,
                "traffic_penalty": 20.0,
            },
            {
                "edge_id": "1-3-0",
                "source_node": "1",
                "target_node": "3",
                "traffic_level": "HIGH",
                "penalty_factor": 3.0,
                "traffic_penalty": 20.0,
            }
        ]
    }

    monkeypatch.setattr(traffic_cost_service, "get_cached_costs", lambda: mock_traffic_costs)

    with test_app.app_context():
        # Normal mode should still take 0 -> 1 -> 3
        res_norm = service.calculate_route("0", "3", algorithm="astar", routing_mode="normal")
        assert [n["id"] for n in res_norm["nodes"]] == ["0", "1", "3"]

        # Traffic aware mode should bypass via 0 -> 2 -> 3
        res_traffic = service.calculate_route("0", "3", algorithm="astar", routing_mode="traffic_aware")
        assert res_traffic["routing_mode"] == "traffic_aware"
        assert [n["id"] for n in res_traffic["nodes"]] == ["0", "2", "3"]
        assert res_traffic["total_distance_km"] == 1.2
        assert res_traffic["base_cost"] == 24.0
        assert res_traffic["traffic_cost"] == 0.0


def test_astar_dijkstra_equivalence(test_app, monkeypatch, mock_graph):
    """Verify A* and Dijkstra find equivalent paths in traffic aware mode."""
    service = RoutingService()

    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)

    mock_traffic_costs = {
        "success": True,
        "version": 99,
        "edge_costs": [
            {
                "edge_id": "0-1-0",
                "source_node": "0",
                "target_node": "1",
                "traffic_level": "MEDIUM",
                "penalty_factor": 1.6,
                "traffic_penalty": 6.0,
            }
        ]
    }

    monkeypatch.setattr(traffic_cost_service, "get_cached_costs", lambda: mock_traffic_costs)

    with test_app.app_context():
        comp = service.compare_algorithms("0", "3", routing_mode="traffic_aware")
        astar_info = comp["comparison"]["astar"]
        dijkstra_info = comp["comparison"]["dijkstra"]

        assert astar_info["total_cost"] == dijkstra_info["total_cost"]
        assert astar_info["distance_km"] == dijkstra_info["distance_km"]


def test_traffic_unavailable_fallback(test_app, monkeypatch, mock_graph):
    """Verify that if traffic service fails, routing gracefully falls back to normal edge costs."""
    service = RoutingService()

    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)

    def failing_get_cached():
        raise RuntimeError("Traffic service unavailable")

    monkeypatch.setattr(traffic_cost_service, "get_cached_costs", failing_get_cached)

    with test_app.app_context():
        res = service.calculate_route("0", "3", algorithm="astar", routing_mode="traffic_aware")
        assert res["status"] == "success"
        assert res["nodes"][1]["id"] == "1"
