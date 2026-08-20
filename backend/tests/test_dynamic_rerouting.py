import pytest
import time
import networkx as nx
from flask import Flask

from app.services.routing_service import RoutingService
from app.modules.road_network.services.graph_service import graph_service
from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service
from app.modules.traffic_intelligence.services.hotspot_service import hotspot_service
import app.modules.vehicle_simulation.services.route_store as route_store


@pytest.fixture(autouse=True)
def clean_route_store():
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
    app.config["REROUTE_COOLDOWN_SECONDS"] = 5
    app.config["COST_CHANGE_THRESHOLD"] = 0.15
    app.config["MIN_ROUTE_IMPROVEMENT"] = 0.10
    app.config["MIN_TRAFFIC_COST_INCREASE_PERCENT"] = 0.15
    app.config["MIN_ETA_INCREASE_PERCENT"] = 0.15
    app.config["MIN_TRAFFIC_CHANGE_LEVEL"] = "MEDIUM"
    app.config["MIN_ROUTE_IMPROVEMENT_PERCENT"] = 0.10
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

    G.add_edge("0", "1", key=0, length=500.0, travel_time=10.0)
    G.add_edge("1", "3", key=0, length=500.0, travel_time=10.0)

    G.add_edge("0", "2", key=0, length=600.0, travel_time=12.0)
    G.add_edge("2", "3", key=0, length=600.0, travel_time=12.0)

    return G


def test_no_active_route(test_app, monkeypatch):
    """Verify evaluate_reroute returns NO_CHANGE if no active route exists."""
    service = RoutingService()
    route_store.clear_route()
    with test_app.app_context():
        res = service.evaluate_reroute()
        assert res["status"] == "NO_CHANGE"
        assert res["recommended"] is False


def test_cooldown_active(test_app, monkeypatch, mock_graph):
    """Verify evaluate_reroute returns COOLDOWN if last reroute was too recent."""
    service = RoutingService()
    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)
    
    # Setup active route
    route_obj = {
        "path_nodes": ["0", "1", "3"],
        "geometry": [[12.9716, 77.5946], [12.9720, 77.5950], [12.9730, 77.5970]],
        "source_node_id": "0",
        "target_node_id": "3",
        "total_distance_km": 1.0,
        "total_duration_seconds": 20.0,
        "total_cost": 20.0,
        "traffic_level": "NONE",
        "eta_minutes": 0.33,
    }
    
    with test_app.app_context():
        route_store.set_route(route_obj, algorithm="astar", routing_mode="traffic_aware")
        route_store.set_last_reroute_time(time.time() - 2)  # Cooldown is 5 seconds
        
        res = service.evaluate_reroute()
        assert res["status"] == "COOLDOWN"
        assert res["recommended"] is False


def test_stable_traffic(test_app, monkeypatch, mock_graph):
    """Verify evaluate_reroute returns MONITORING if traffic is stable and optimal."""
    service = RoutingService()
    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)
    
    route_obj = {
        "path_nodes": ["0", "1", "3"],
        "geometry": [[12.9716, 77.5946], [12.9720, 77.5950], [12.9730, 77.5970]],
        "source_node_id": "0",
        "target_node_id": "3",
        "total_distance_km": 1.0,
        "total_duration_seconds": 20.0,
        "total_cost": 20.0,
        "traffic_level": "NONE",
        "eta_minutes": 0.33,
    }
    
    mock_traffic_costs = {"success": True, "edge_costs": []}
    monkeypatch.setattr(traffic_cost_service, "get_cached_costs", lambda: mock_traffic_costs)
    
    with test_app.app_context():
        route_store.set_route(route_obj, algorithm="astar", routing_mode="traffic_aware")
        route_store.set_last_reroute_time(time.time() - 10)  # Cooldown expired
        
        res = service.evaluate_reroute()
        assert res["status"] == "MONITORING"
        assert res["recommended"] is False


def test_route_degraded_and_alternative_found(test_app, monkeypatch, mock_graph):
    """Verify evaluate_reroute returns REROUTE_AVAILABLE when route is degraded and alternative is better."""
    service = RoutingService()
    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)
    
    route_obj = {
        "path_nodes": ["0", "1", "3"],
        "geometry": [[12.9716, 77.5946], [12.9720, 77.5950], [12.9730, 77.5970]],
        "source_node_id": "0",
        "target_node_id": "3",
        "total_distance_km": 1.0,
        "total_duration_seconds": 20.0,
        "total_cost": 20.0,
        "traffic_level": "NONE",
        "eta_minutes": 0.33,
    }
    
    # Introduce high traffic on 0->1->3 (edge travel time penalty factor 3.0)
    mock_traffic_costs = {
        "success": True,
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
        route_store.set_route(route_obj, algorithm="astar", routing_mode="traffic_aware")
        # Ensure we record original cost properly
        route_store.set_original_cost(20.0)
        route_store.set_last_reroute_time(time.time() - 10)
        
        res = service.evaluate_reroute()
        assert res["status"] == "REROUTE_AVAILABLE"
        assert res["recommended"] is True
        assert res["alternative_route"]["distance_km"] == 1.2
        assert res["improvement_percent"] > 0


def test_loop_prevention(test_app, monkeypatch, mock_graph):
    """Verify loop prevention demands higher improvement threshold to oscillation back."""
    service = RoutingService()
    monkeypatch.setattr(graph_service, "get_nx_graph_safe", lambda: mock_graph)
    
    # Current active route is 0->2->3 (longer, cost 24.0)
    route_obj = {
        "path_nodes": ["0", "2", "3"],
        "geometry": [[12.9716, 77.5946], [12.9710, 77.5960], [12.9730, 77.5970]],
        "source_node_id": "0",
        "target_node_id": "3",
        "total_distance_km": 1.2,
        "total_duration_seconds": 24.0,
        "total_cost": 24.0,
        "traffic_level": "NONE",
        "eta_minutes": 0.4,
    }
    
    # Previous route was 0->1->3
    prev_route_obj = {
        "path_nodes": ["0", "1", "3"],
        "geometry": [[12.9716, 77.5946], [12.9720, 77.5950], [12.9730, 77.5970]],
    }
    
    # Setup traffic so that current route 0->2->3 is slightly degraded (cost 24.0 -> 24.48),
    # but switching back to previous route 0->1->3 offers only minor improvement (say 18.3%, below loop threshold of 20%)
    mock_traffic_costs = {
        "success": True,
        "edge_costs": [
            {
                "edge_id": "0-2-0",
                "source_node": "0",
                "target_node": "2",
                "traffic_level": "MEDIUM",
                "penalty_factor": 1.04,
                "traffic_penalty": 0.48,
            }
        ]
    }
    monkeypatch.setattr(traffic_cost_service, "get_cached_costs", lambda: mock_traffic_costs)
    
    with test_app.app_context():
        route_store.set_route(route_obj, algorithm="astar", routing_mode="traffic_aware")
        route_store.set_original_cost(24.0)
        route_store.set_last_reroute_time(time.time() - 10)
        
        # Explicitly set previous route in store
        route_store._previous_route = prev_route_obj
        route_store._previous_route_cost = 20.0
        
        res = service.evaluate_reroute()
        # Normal threshold of 10% is satisfied, but because of loop prevention (requires 20%), it should not reroute
        assert res["status"] == "NO_BETTER_ROUTE"
        assert res["recommended"] is False
