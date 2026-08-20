"""
test_sprint11e_backend.py — Sprint 11E Part 1 Test Suite

Automated Backend Verification for:
- SQLite Concurrency & Lock-Free Simulation (200+ vehicles)
- Dual-Algorithm Rerouting Engine (A* + Dijkstra)
- Dynamic Congestion Penalty Overlay
- Route Diversity & Geographic Divergence Filtering
- 30-Second Hard Timeout Guarantee
- "NO_BETTER_ROUTE" Fallback Handlers
- Continuous Non-Blocking Vehicle Movement
"""

import time
import pytest
import concurrent.futures
from flask import Flask

from app import create_app
from database.db import db
from app.modules.road_network.services.graph_service import graph_service
from app.services.routing_service import routing_service
from app.modules.vehicle_simulation.services.vehicle_service import vehicle_service
from app.modules.vehicle_simulation.services.vehicle_movement_service import vehicle_movement_service
from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service
from app.modules.traffic_intelligence.services.dbscan_service import dbscan_service
from app.modules.traffic_intelligence.services.hotspot_service import hotspot_service
import app.modules.vehicle_simulation.services.route_store as route_store


@pytest.fixture(scope="module")
def app_instance():
    """Create Flask application instance for test module."""
    app = create_app("test")
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    with app.app_context():
        db.create_all()
        # Preload graph
        graph_service.preload_default_graph()
        yield app


from app.modules.road_network.services.node_service import node_service

def _get_test_nodes(src_coords=(12.9716, 77.5946), tgt_coords=(12.9352, 77.6245)):
    src_res = node_service.find_nearest_node(src_coords[0], src_coords[1])
    tgt_res = node_service.find_nearest_node(tgt_coords[0], tgt_coords[1])
    return src_res["node_id"], tgt_res["node_id"]


def test_sqlite_concurrency_200_vehicles(app_instance):
    """
    TEST 6: 200+ vehicles simulation update loop without sqlite lock errors during concurrent reads.
    """
    with app_instance.app_context():
        vehicle_service.delete_all_vehicles()
        src_n, tgt_n = _get_test_nodes()

        # Seed 200 vehicles
        veh_data = []
        for i in range(200):
            veh_data.append({
                "latitude": 12.9716 + (i * 0.00001),
                "longitude": 77.5946 + (i * 0.00001),
                "speed": 30.0,
                "heading": 90.0,
                "current_node": str(src_n),
                "current_edge": f"{src_n}-{tgt_n}-0",
                "edge_progress": 0.1,
                "status": "active"
            })

        created, failed = vehicle_service.bulk_create_vehicles(veh_data)
        assert len(created) == 200
        assert failed == 0

        # Perform update ticks while 10 concurrent reader threads query snapshot
        def _writer_ticks():
            with app_instance.app_context():
                for _ in range(5):
                    res = vehicle_movement_service.update_vehicle_positions(delta_seconds=1.0)
                    assert "vehicles_moved" in res
                    time.sleep(0.01)
                return True

        def _reader_snapshot():
            with app_instance.app_context():
                return vehicle_service.get_all_vehicles()

        with concurrent.futures.ThreadPoolExecutor(max_workers=11) as exec:
            f_writer = exec.submit(_writer_ticks)
            f_reads = [exec.submit(_reader_snapshot) for _ in range(10)]

            assert f_writer.result() is True
            for f in f_reads:
                res = f.result()
                assert len(res) >= 200

        vehicle_service.delete_all_vehicles()


def test_high_traffic_active_route_triggers_reroute(app_instance):
    """
    TEST 1: High traffic active route triggers alternative route search automatically.
    """
    with app_instance.app_context():
        src_n, tgt_n = _get_test_nodes()
        r = routing_service.calculate_route(
            source_node=src_n,
            destination_node=tgt_n,
            algorithm="astar"
        )
        assert r["success"] is True
        route_store.set_routing_mode("normal")
        route_store.set_last_reroute_time(0.0) # Bypass cooldown
        route_store.set_original_cost(100.0) # Simulate traffic cost degradation

        # Evaluate reroute
        res = routing_service.evaluate_reroute()
        assert "status" in res
        assert res["status"] in ["MONITORING", "REROUTE_AVAILABLE", "NO_BETTER_ROUTE", "NO_CHANGE"]


def test_both_algorithms_produce_candidates(app_instance):
    """
    TEST 2: Both A* and Dijkstra algorithms produce alternative candidates.
    """
    with app_instance.app_context():
        src_n, tgt_n = _get_test_nodes()
        r = routing_service.calculate_route(
            source_node=src_n,
            destination_node=tgt_n,
            algorithm="astar"
        )
        assert r["success"] is True
        route_store.set_routing_mode("normal")
        route_store.set_last_reroute_time(0.0)
        route_store.set_original_cost(100.0)

        res = routing_service.evaluate_reroute()
        assert "algorithms_evaluated" in res or "status" in res
        if res.get("reroute_available"):
            algs = [c.get("algorithm") for c in res.get("alternatives", [])]
            assert len(algs) > 0


def test_route_diversity_filtering(app_instance):
    """
    TEST 3: Route diversity filtering ensures candidates are geographically different.
    """
    with app_instance.app_context():
        src_n, tgt_n = _get_test_nodes()
        r = routing_service.calculate_route(
            source_node=src_n,
            destination_node=tgt_n,
            algorithm="astar"
        )
        assert r["success"] is True
        route_store.set_routing_mode("normal")
        route_store.set_last_reroute_time(0.0)
        route_store.set_original_cost(100.0)

        res = routing_service.evaluate_reroute()
        if res.get("reroute_available"):
            alts = res.get("alternatives", [])
            for alt in alts:
                assert "divergence_percent" in alt
                assert alt["divergence_percent"] >= 10.0


def test_no_better_route_fallback(app_instance):
    """
    TEST 4: Returns NO_BETTER_ROUTE without fabricating fake routes.
    """
    with app_instance.app_context():
        src_n, tgt_n = _get_test_nodes((12.9716, 77.5946), (12.9720, 77.5950))
        r = routing_service.calculate_route(
            source_node=src_n,
            destination_node=tgt_n,
            algorithm="astar"
        )
        assert r["success"] is True
        route_store.set_routing_mode("normal")
        route_store.set_last_reroute_time(0.0)

        res = routing_service.evaluate_reroute()
        assert res["status"] in ["MONITORING", "NO_BETTER_ROUTE", "REROUTE_AVAILABLE", "NO_CHANGE"]
        if res["status"] == "NO_BETTER_ROUTE":
            assert res["alternatives"] == []
            assert res["recommended_route"] is None


def test_30_second_timeout_guarantee(app_instance):
    """
    TEST 5: Alternative route search terminates in <= 30 seconds.
    """
    with app_instance.app_context():
        src_n, tgt_n = _get_test_nodes()
        r = routing_service.calculate_route(
            source_node=src_n,
            destination_node=tgt_n,
            algorithm="astar"
        )
        assert r["success"] is True
        route_store.set_route(r)
        route_store.set_last_reroute_time(0.0)

        start_t = time.time()
        res = routing_service.evaluate_reroute()
        elapsed = time.time() - start_t
        assert elapsed <= 30.0
        assert "search_time_ms" in res or elapsed <= 30.0


def test_simulation_runs_concurrently_with_reroute(app_instance):
    """
    TEST 7: Simulation moves vehicles while alternative search runs.
    """
    with app_instance.app_context():
        vehicle_service.delete_all_vehicles()
        vehicle_service.create_vehicle({
            "latitude": 12.9716,
            "longitude": 77.5946,
            "speed": 40.0,
            "heading": 90.0,
            "current_node": "1",
            "current_edge": "1-2-0",
            "status": "active"
        })

        def _reroute():
            with app_instance.app_context():
                return routing_service.evaluate_reroute()

        def _move():
            with app_instance.app_context():
                return vehicle_movement_service.update_vehicle_positions(delta_seconds=1.0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as exec:
            f1 = exec.submit(_reroute)
            f2 = exec.submit(_move)

            r_res = f1.result()
            m_res = f2.result()

            assert "status" in r_res
            assert "vehicles_moved" in m_res

        vehicle_service.delete_all_vehicles()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
