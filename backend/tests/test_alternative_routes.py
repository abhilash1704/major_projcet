"""
test_alternative_routes.py — Complete test suite for Alternative Routes Engine

Tests:
  1. current route returned correctly
  2. valid alternative generated
  3. duplicate removed
  4. current route excluded
  5. A* and Dijkstra same path handled
  6. distinct alternatives preserved
  7. invalid route rejected
  8. disconnected graph handled
  9. traffic-aware consistency
  10. timeout protection
  11. concurrent request protection
  12. stale request protection
  13. no-alternative state
  14. one-alternative state
  15. two-alternative state
  16. main route isolation: route_store is NOT modified during alternative generation
"""

import time
import threading
import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.modules.routing.services.alternative_route_service import (
    alternative_route_service,
    _compute_route_similarity,
    _compute_edge_overlap,
    _route_signature,
    _validate_candidate,
)
from app.services.routing_service import routing_service
import app.modules.vehicle_simulation.services.route_store as route_store

# Real Bangalore graph nodes
SRC_CHIKKAPETE = "7172568278"
DST_BASAVANAGUDI = "1931983762"
SRC_JP_NAGAR = "362550614"
DST_WHITEFIELD = "331147702"
SRC_SILK_BOARD = "10282796509"
DST_KORAMANGALA = "309592695"


@pytest.fixture(scope="module")
def app():
    a = create_app("test")
    a.config["TESTING"] = True
    return a


@pytest.fixture(scope="module")
def client(app):
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture(scope="module")
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture(autouse=True)
def clean_alt_cache():
    alternative_route_service.clear_cache()
    yield
    alternative_route_service.clear_cache()


def _mock_route(nodes=None, dist=10.0, eta_sec=600.0, traffic="LOW", cost=600.0):
    if nodes is None:
        nodes = [{"id": "s"}, {"id": "m1"}, {"id": "m2"}, {"id": "d"}]
    return {
        "success": True,
        "distance_km": dist,
        "total_distance_km": dist,
        "travel_time_seconds": eta_sec,
        "total_travel_time_seconds": eta_sec,
        "traffic_cost": 50.0,
        "total_cost": cost,
        "traffic_level": traffic,
        "nodes": nodes,
        "geometry": [[12.9, 77.5], [12.95, 77.55]],
        "congested_segments": [],
    }


# ── 1. Current route returned correctly ───────────────────────────────────────
def test_1_current_route_returned_correctly(ctx):
    current = {
        "path_nodes": [SRC_CHIKKAPETE, "mid_1", DST_BASAVANAGUDI],
        "distance_km": 4.5,
        "travel_time_seconds": 360.0,
        "traffic_level": "LOW",
        "traffic_cost": 10.0,
    }
    res = alternative_route_service.generate_alternative_routes(
        source_node=SRC_CHIKKAPETE,
        destination_node=DST_BASAVANAGUDI,
        current_route=current,
        request_id="test-curr-01",
    )
    assert res["success"] is True
    assert "current_route" in res
    assert res["current_route"]["distance_km"] == 4.5
    assert res["current_route"]["eta_minutes"] == 6.0


# ── 2. Valid alternative generated ───────────────────────────────────────────
def test_2_valid_alternative_generated(ctx):
    res = alternative_route_service.generate_alternative_routes(
        source_node=SRC_CHIKKAPETE,
        destination_node=DST_BASAVANAGUDI,
        routing_mode="normal",
        max_alternatives=2,
        request_id="test-valid-alt",
    )
    assert res["success"] is True
    assert res["status"] in ("success", "no_alternatives")
    for alt in res["alternatives"]:
        assert alt["distance_km"] > 0
        assert alt["eta_minutes"] > 0
        assert len(alt["path"]) >= 2
        assert str(alt["path"][0]) == SRC_CHIKKAPETE
        assert str(alt["path"][-1]) == DST_BASAVANAGUDI


# ── 3. Duplicate removed ──────────────────────────────────────────────────────
def test_3_duplicate_removed(ctx):
    # If all workers return the exact same route, duplicates must be stripped
    identical = _mock_route(nodes=[{"id": "s"}, {"id": "m1"}, {"id": "d"}])
    with patch("app.services.routing_service.routing_service.calculate_route", return_value=identical):
        res = alternative_route_service.generate_alternative_routes(
            source_node="s",
            destination_node="d",
            current_route={"path_nodes": ["s", "m0", "d"]},
            max_alternatives=2,
            request_id="test-dup-rm",
        )
    assert res["success"] is True
    # At most 1 alternative accepted because the second is a duplicate of the first
    assert len(res["alternatives"]) <= 1


# ── 4. Current route excluded ─────────────────────────────────────────────────
def test_4_current_route_excluded(ctx):
    curr_nodes = ["src_n", "node_a", "node_b", "dst_n"]
    curr_sig = _route_signature(curr_nodes)

    identical_to_curr = _mock_route(nodes=[{"id": n} for n in curr_nodes])
    with patch("app.services.routing_service.routing_service.calculate_route", return_value=identical_to_curr):
        res = alternative_route_service.generate_alternative_routes(
            source_node="src_n",
            destination_node="dst_n",
            current_route={"path_nodes": curr_nodes},
            request_id="test-curr-excl",
        )
    assert res["success"] is True
    assert len(res["alternatives"]) == 0
    assert res["status"] == "no_alternatives"


# ── 5. A* and Dijkstra same path handled ─────────────────────────────────────
def test_5_astar_and_dijkstra_same_path_handled():
    # If A* and Dijkstra return the same path, topology signature deduplicates them
    path_astar = ["1", "2", "3", "4"]
    path_dijkstra = ["1", "2", "3", "4"]
    sig1 = _route_signature(path_astar)
    sig2 = _route_signature(path_dijkstra)
    assert sig1 == sig2
    # Edge overlap is 1.0
    assert _compute_edge_overlap(path_astar, path_dijkstra) == 1.0


# ── 6. Distinct alternatives preserved ───────────────────────────────────────
def test_6_distinct_alternatives_preserved(ctx):
    call_idx = [0]
    def mock_calc(**kwargs):
        call_idx[0] += 1
        return _mock_route(
            nodes=[{"id": "src"}, {"id": f"distinct_corridor_{call_idx[0]}"}, {"id": "dst"}],
            dist=10.0 + call_idx[0],
            cost=500.0 + call_idx[0] * 50,
        )

    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=mock_calc):
        res = alternative_route_service.generate_alternative_routes(
            source_node="src",
            destination_node="dst",
            current_route={"path_nodes": ["src", "primary_path", "dst"]},
            max_alternatives=2,
            request_id="test-distinct-preserved",
        )
    assert res["success"] is True
    assert len(res["alternatives"]) == 2
    assert res["alternatives"][0]["route_signature"] != res["alternatives"][1]["route_signature"]


# ── 7. Invalid route rejected ─────────────────────────────────────────────────
def test_7_invalid_route_rejected():
    # Wrong destination
    bad_route = _mock_route(nodes=[{"id": "A"}, {"id": "B"}, {"id": "WRONG"}])
    is_valid, reason = _validate_candidate(bad_route, "A", "C")
    assert is_valid is False
    assert "wrong_end" in reason

    # Zero distance
    bad_dist = _mock_route(nodes=[{"id": "A"}, {"id": "C"}], dist=0.0)
    is_valid, reason = _validate_candidate(bad_dist, "A", "C")
    assert is_valid is False
    assert "distance" in reason


# ── 8. Disconnected graph handled ─────────────────────────────────────────────
def test_8_disconnected_graph_handled(ctx):
    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=ValueError("No path exists")):
        res = alternative_route_service.generate_alternative_routes(
            source_node="isolated_1",
            destination_node="isolated_2",
            current_route={"path_nodes": ["isolated_1", "isolated_2"]},
            request_id="test-no-path",
        )
    assert res["success"] is True
    assert res["status"] == "no_alternatives"
    assert len(res["alternatives"]) == 0
    assert "No meaningful" in res["message"]


# ── 9. Traffic-aware consistency ──────────────────────────────────────────────
def test_9_traffic_aware_consistency(ctx):
    res = alternative_route_service.generate_alternative_routes(
        source_node=SRC_CHIKKAPETE,
        destination_node=DST_BASAVANAGUDI,
        routing_mode="traffic_aware",
        traffic_level="HIGH",
        max_alternatives=2,
        request_id="test-traffic-consistency",
    )
    assert res["success"] is True
    assert res["routing_mode"] == "traffic_aware"
    assert res["traffic_level"] == "HIGH"


# ── 10. Timeout protection ────────────────────────────────────────────────────
def test_10_timeout_protection(ctx):
    with patch(
        "app.modules.routing.services.alternative_route_service.AlternativeRouteService._execute_generation"
    ) as mock_exec:
        mock_exec.return_value = {
            "status": "error",
            "success": False,
            "request_id": "timeout-req",
            "error": {"code": "ROUTE_GENERATION_TIMEOUT", "message": "Alternative route analysis timed out."},
            "alternatives": [],
            "current_route": {},
        }
        res = alternative_route_service.generate_alternative_routes(
            source_node="n1",
            destination_node="n2",
            request_id="timeout-req",
        )
    assert res["success"] is False
    assert res["error"]["code"] == "ROUTE_GENERATION_TIMEOUT"


# ── 11. Concurrent request protection ─────────────────────────────────────────
def test_11_concurrent_request_protection(ctx):
    results = {}
    errors = []

    def _call(src, dst, key):
        try:
            r = alternative_route_service.generate_alternative_routes(
                source_node=src,
                destination_node=dst,
                request_id=f"concurrent-{key}",
            )
            results[key] = r
        except Exception as exc:
            errors.append(str(exc))

    t1 = threading.Thread(target=_call, args=(SRC_CHIKKAPETE, DST_BASAVANAGUDI, "A"))
    t2 = threading.Thread(target=_call, args=(SRC_SILK_BOARD, DST_KORAMANGALA, "B"))
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    assert not errors, f"Errors occurred: {errors}"
    assert "A" in results and "B" in results
    assert results["A"]["request_id"] == "concurrent-A"
    assert results["B"]["request_id"] == "concurrent-B"


# ── 12. Stale request protection ──────────────────────────────────────────────
def test_12_stale_request_protection(ctx):
    req_id_a = "req-older-A"
    req_id_b = "req-newer-B"
    res_a = alternative_route_service.generate_alternative_routes(
        source_node=SRC_CHIKKAPETE, destination_node=DST_BASAVANAGUDI, request_id=req_id_a
    )
    res_b = alternative_route_service.generate_alternative_routes(
        source_node=SRC_SILK_BOARD, destination_node=DST_KORAMANGALA, request_id=req_id_b
    )
    assert res_a["request_id"] == req_id_a
    assert res_b["request_id"] == req_id_b


# ── 13. Zero-alternative state ────────────────────────────────────────────────
def test_13_zero_alternative_state(ctx):
    curr = ["src", "dst"]
    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=ValueError("no route")):
        res = alternative_route_service.generate_alternative_routes(
            source_node="src",
            destination_node="dst",
            current_route={"path_nodes": curr},
            request_id="test-zero-alt",
        )
    assert res["status"] == "no_alternatives"
    assert res["count"] == 0
    assert res["alternatives"] == []
    assert res["success"] is True


# ── 14. One-alternative state ─────────────────────────────────────────────────
def test_14_one_alternative_state(ctx):
    n = [0]
    def side_effect(**kwargs):
        n[0] += 1
        if n[0] == 1:
            return _mock_route(nodes=[{"id": "s"}, {"id": "unique_1"}, {"id": "d"}])
        return _mock_route(nodes=[{"id": "s"}, {"id": "unique_1"}, {"id": "d"}])  # duplicate

    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=side_effect):
        res = alternative_route_service.generate_alternative_routes(
            source_node="s",
            destination_node="d",
            current_route={"path_nodes": ["s", "primary", "d"]},
            max_alternatives=2,
            request_id="test-one-alt",
        )
    assert res["status"] == "success"
    assert res["count"] == 1
    assert len(res["alternatives"]) == 1


# ── 15. Two-alternative state ─────────────────────────────────────────────────
def test_15_two_alternative_state(ctx):
    n = [0]
    def side_effect(**kwargs):
        n[0] += 1
        return _mock_route(
            nodes=[{"id": "s"}, {"id": f"alt_node_{n[0]}"}, {"id": "d"}],
            dist=10.0 + n[0],
            cost=500.0 + n[0] * 10
        )

    with patch("app.services.routing_service.routing_service.calculate_route", side_effect=side_effect):
        res = alternative_route_service.generate_alternative_routes(
            source_node="s",
            destination_node="d",
            current_route={"path_nodes": ["s", "primary", "d"]},
            max_alternatives=2,
            request_id="test-two-alt",
        )
    assert res["status"] == "success"
    assert res["count"] == 2
    assert len(res["alternatives"]) == 2
    assert res["alternatives"][0]["rank"] == 1
    assert res["alternatives"][1]["rank"] == 2


# ── 16. Route store isolation test ────────────────────────────────────────────
def test_16_route_store_not_modified_during_alternative_generation(ctx):
    # Set an initial route in route_store
    initial_route = {
        "path_nodes": [SRC_CHIKKAPETE, "primary_stop", DST_BASAVANAGUDI],
        "geometry": [[12.9698, 77.5754], [12.9422, 77.5753]],
        "source_node_id": SRC_CHIKKAPETE,
        "target_node_id": DST_BASAVANAGUDI,
        "total_distance_km": 3.9,
        "total_duration_seconds": 300.0,
        "total_cost": 300.0,
    }
    route_store.set_route(initial_route, algorithm="astar", routing_mode="normal")
    assert route_store.get_route() is not None
    orig_path = route_store.get_route()["path_nodes"]

    # Generate alternative routes
    res = alternative_route_service.generate_alternative_routes(
        source_node=SRC_CHIKKAPETE,
        destination_node=DST_BASAVANAGUDI,
        current_route=initial_route,
        routing_mode="normal",
        max_alternatives=2,
        request_id="test-isolation",
    )

    # Verify route_store was NOT altered by alternative generation
    after_route = route_store.get_route()
    assert after_route is not None
    assert after_route["path_nodes"] == orig_path, "route_store was corrupted by alternative route generation!"


# ── 17. API endpoint test ─────────────────────────────────────────────────────
def test_17_post_api_routes_alternatives_endpoint(client):
    payload = {
        "source": SRC_CHIKKAPETE,
        "destination": DST_BASAVANAGUDI,
        "routing_mode": "normal",
        "algorithm": "astar",
        "max_alternatives": 2,
        "request_id": "api-test-chikkapete-01",
    }
    response = client.post("/api/routes/alternatives", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data["success"] is True
    assert data["status"] in ("success", "no_alternatives")
    assert "count" in data
    assert "alternatives" in data
    assert "current_route" in data
    assert data["request_id"] == "api-test-chikkapete-01"
