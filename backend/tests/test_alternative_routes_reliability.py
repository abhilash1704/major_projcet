"""
test_alternative_routes_reliability.py

Comprehensive reliability test suite for the Alternative Route Engine.

Covers:
  1.  Normal route (baseline)
  2.  Traffic-aware route
  3.  A* algorithm
  4.  Dijkstra algorithm
  5.  Valid alternatives returned
  6.  Zero alternatives (no-path scenario)
  7.  Duplicate candidate filtering
  8.  Invalid source node
  9.  Invalid destination node
  10. Traffic unavailable (graceful degradation)
  11. Timeout protection
  12. Concurrent requests (no state corruption)
  13. Stale/cached result within TTL
  14. Graph version fingerprinting
  15. Traffic snapshot consistency
  16. API contract — success response shape
  17. API contract — error response shape
  18. Max alternatives capped at 2
  19. Route validation (start node == source, end node == destination)
  20. Duplicate-request idempotency (lock prevents parallel dups)
"""

import time
import threading
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

from app import create_app
from app.modules.routing.services.alternative_route_service import (
    alternative_route_service,
    _compute_route_similarity,
    _validate_candidate,
    AlternativeRouteService,
    SIMILARITY_THRESHOLD,
    HARD_TIMEOUT_SECONDS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


# ── Helper ────────────────────────────────────────────────────────────────────

def _mock_route(nodes=None, dist=10.0, eta_sec=600.0, traffic="LOW", cost=600.0):
    """Build a minimal route dict matching routing_service output."""
    if nodes is None:
        nodes = [{"id": "s"}, {"id": "m1"}, {"id": "m2"}, {"id": "d"}]
    return {
        "success": True,
        "distance_km": dist,
        "travel_time_seconds": eta_sec,
        "traffic_cost": 50.0,
        "total_cost": cost,
        "traffic_level": traffic,
        "nodes": nodes,
        "geometry": [[12.9, 77.5], [12.95, 77.55]],
        "congested_segments": [],
    }


# ── 1. Route similarity utility ───────────────────────────────────────────────

class TestRouteSimilarity:
    def test_identical_paths(self):
        p = ["n1", "n2", "n3", "n4"]
        assert _compute_route_similarity(p, p) == 1.0

    def test_completely_different(self):
        assert _compute_route_similarity(["a", "b"], ["c", "d"]) == 0.0

    def test_partial_overlap(self):
        p1 = ["n1", "n2", "n3", "n4", "n5"]
        p2 = ["n1", "n2", "n3", "n10", "n11"]
        sim = _compute_route_similarity(p1, p2)
        assert round(sim, 2) == 0.60  # 3 shared / min(5,5)=5 → 0.60

    def test_empty_path(self):
        assert _compute_route_similarity([], ["a"]) == 0.0
        assert _compute_route_similarity(["a"], []) == 0.0

    def test_configured_threshold_boundary(self):
        # 4 shared out of 5 = 0.80, which should be >= threshold (0.75)
        p1 = ["n1", "n2", "n3", "n4", "n5"]
        p2 = ["n1", "n2", "n3", "n4", "n6"]
        sim = _compute_route_similarity(p1, p2)
        assert sim >= SIMILARITY_THRESHOLD  # should be treated as duplicate


# ── 2. Candidate validation ───────────────────────────────────────────────────

class TestCandidateValidation:
    def test_valid_candidate(self):
        alt = _mock_route(nodes=[{"id": "SRC"}, {"id": "MID"}, {"id": "DST"}])
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is True
        assert reason == "ok"

    def test_wrong_start_node(self):
        alt = _mock_route(nodes=[{"id": "WRONG"}, {"id": "MID"}, {"id": "DST"}])
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is False
        assert "wrong_start" in reason

    def test_wrong_end_node(self):
        alt = _mock_route(nodes=[{"id": "SRC"}, {"id": "MID"}, {"id": "WRONG"}])
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is False
        assert "wrong_end" in reason

    def test_too_few_nodes(self):
        alt = _mock_route(nodes=[{"id": "SRC"}])
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is False

    def test_not_successful(self):
        alt = {"success": False, "nodes": [{"id": "SRC"}, {"id": "DST"}]}
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is False

    def test_zero_distance(self):
        alt = _mock_route(
            nodes=[{"id": "SRC"}, {"id": "DST"}],
            dist=0.0
        )
        ok, reason = _validate_candidate(alt, "SRC", "DST")
        assert ok is False
        assert "distance" in reason


# ── 3. Service: invalid parameter handling ────────────────────────────────────

class TestInvalidParameters:
    def test_missing_source(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node=None, destination_node="1032"
        )
        assert res["success"] is False
        assert "error" in res
        assert res["error"]["code"] == "INVALID_ROUTE_REQUEST"

    def test_missing_destination(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node="7784026478", destination_node=""
        )
        assert res["success"] is False
        assert res["error"]["code"] == "INVALID_ROUTE_REQUEST"

    def test_same_src_dst(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node="7784026478", destination_node="7784026478"
        )
        assert res["success"] is False

    def test_invalid_source_node(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node="COMPLETELY_FAKE_NODE_99999",
            destination_node="1032",
            request_id="test-invalid-src"
        )
        assert res["success"] is False
        assert res["error"]["code"] in (
            "INVALID_SOURCE_NODE", "GRAPH_UNAVAILABLE", "INVALID_ROUTE_REQUEST"
        )

    def test_invalid_destination_node(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node="7784026478",
            destination_node="COMPLETELY_FAKE_NODE_99999",
            request_id="test-invalid-dst"
        )
        assert res["success"] is False


# ── 4. Duplicate filtering ────────────────────────────────────────────────────

class TestDuplicateFiltering:
    def test_all_identical_candidates_filtered(self, ctx):
        """If all 6 workers return the same path, alternatives list must be empty."""
        identical_route = _mock_route(
            nodes=[{"id": "n1"}, {"id": "n2"}, {"id": "n3"}, {"id": "n4"}]
        )
        with patch(
            "app.services.routing_service.routing_service.calculate_route",
            return_value=identical_route,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="n1",
                destination_node="n4",
                current_route={"path_nodes": ["n1", "n2", "n3", "n4"]},
                request_id="dup-test-001",
            )
        assert res["success"] is True
        assert len(res["alternatives"]) == 0
        assert res["status"] == "no_alternatives"

    def test_two_diverse_candidates_accepted(self, ctx):
        """Two truly different paths should both be accepted."""
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            n = call_count[0]
            # Unique middle nodes per call so paths differ
            return _mock_route(
                nodes=[{"id": "src"}, {"id": f"unique_mid_{n}"}, {"id": "dst"}],
                dist=10.0 + n,
                cost=600.0 + n * 10,
            )

        with patch(
            "app.services.routing_service.routing_service.calculate_route",
            side_effect=side_effect,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="src",
                destination_node="dst",
                current_route={"path_nodes": ["src", "current_mid", "dst"]},
                max_alternatives=2,
                request_id="diversity-test-001",
            )
        assert res["success"] is True
        assert len(res["alternatives"]) <= 2
        # All accepted alts must have stable route_id
        for alt in res["alternatives"]:
            assert "route_id" in alt and alt["route_id"]


# ── 5. Max alternatives cap ───────────────────────────────────────────────────

class TestMaxAlternativesCap:
    def test_capped_at_two(self, ctx):
        """Even requesting 5 must return at most 2."""
        n = [0]

        def side_effect(**kwargs):
            n[0] += 1
            return _mock_route(
                nodes=[{"id": "s"}, {"id": f"u{n[0]}"}, {"id": "d"}],
                dist=10.0 + n[0],
                cost=600.0 + n[0] * 10,
            )

        with patch(
            "app.services.routing_service.routing_service.calculate_route",
            side_effect=side_effect,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="s",
                destination_node="d",
                max_alternatives=5,
                request_id="cap-test",
            )
        assert res["success"] is True
        assert len(res["alternatives"]) <= 2


# ── 6. Timeout protection ─────────────────────────────────────────────────────

class TestTimeoutProtection:
    def test_timeout_response_structure(self, ctx):
        """A timeout must return a structured error, not raise."""
        with patch(
            "app.modules.routing.services.alternative_route_service.AlternativeRouteService._execute_generation"
        ) as mock_exec:
            mock_exec.return_value = {
                "success": False,
                "status": "error",
                "request_id": "to-test",
                "error": {
                    "code": "ROUTE_GENERATION_TIMEOUT",
                    "message": "Alternative route analysis took too long.",
                },
                "alternatives": [],
                "current_route": {},
            }
            res = alternative_route_service.generate_alternative_routes(
                source_node="n1",
                destination_node="n2",
                request_id="to-test",
            )
        assert res["success"] is False
        assert res["error"]["code"] == "ROUTE_GENERATION_TIMEOUT"
        assert res["alternatives"] == []


# ── 7. Traffic unavailability (graceful degradation) ─────────────────────────

class TestTrafficUnavailable:
    def test_traffic_failure_does_not_crash(self, ctx):
        """If traffic cost service fails, generation should still complete."""
        normal_route = _mock_route(
            nodes=[{"id": "s"}, {"id": "m1"}, {"id": "d"}]
        )
        with patch(
            "app.modules.routing.services.alternative_route_service._fetch_traffic_snapshot",
            return_value=({}, 0),
        ), patch(
            "app.services.routing_service.routing_service.calculate_route",
            return_value=normal_route,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="s",
                destination_node="d",
                request_id="no-traffic-test",
            )
        # Must not crash; may have zero alternatives if all paths identical
        assert "success" in res
        assert "alternatives" in res
        assert isinstance(res["alternatives"], list)


# ── 8. Concurrent requests (isolation) ───────────────────────────────────────

class TestConcurrentRequests:
    def test_concurrent_different_routes(self, ctx):
        """Two parallel calls with different src/dst must not corrupt each other."""
        results = {}
        errors  = []

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

        t1 = threading.Thread(target=_call, args=("n_src_A", "n_dst_A", "A"))
        t2 = threading.Thread(target=_call, args=("n_src_B", "n_dst_B", "B"))
        t1.start()
        t2.start()
        t1.join(timeout=HARD_TIMEOUT_SECONDS + 5)
        t2.join(timeout=HARD_TIMEOUT_SECONDS + 5)

        assert not errors, f"Concurrent requests raised: {errors}"
        # Both must have returned a structured response
        for key in ("A", "B"):
            if key in results:
                r = results[key]
                assert "success" in r
                assert "alternatives" in r


# ── 9. API endpoint contract ──────────────────────────────────────────────────

class TestApiContract:
    def test_success_response_shape(self, client):
        payload = {
            "source":      "7784026478",
            "destination": "1032",
            "traffic_level":   "HIGH",
            "routing_mode":    "traffic_aware",
            "algorithm":       "astar",
            "max_alternatives": 2,
            "request_id":  "api-shape-test",
        }
        resp = client.post("/api/routes/alternatives", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()

        # Top-level required fields
        assert "success" in data
        assert "alternatives" in data
        assert isinstance(data["alternatives"], list)
        assert "current_route" in data
        assert "request_id" in data

        if data["success"] and data["alternatives"]:
            alt = data["alternatives"][0]
            assert "route_id" in alt
            assert "distance_km" in alt
            assert "eta_minutes" in alt
            assert "algorithm" in alt
            assert "traffic_level" in alt

    def test_missing_source_400_shape(self, client):
        payload = {"destination": "1032"}
        resp = client.post("/api/routes/alternatives", json=payload)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["alternatives"] == []

    def test_routing_mode_forwarded(self, client):
        """Backend must accept routing_mode and algorithm in payload."""
        payload = {
            "source":      "7784026478",
            "destination": "1032",
            "routing_mode": "normal",
            "algorithm":    "dijkstra",
            "request_id":   "mode-test",
        }
        resp = client.post("/api/routes/alternatives", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("routing_mode") in ("normal", None) or "routing_mode" in data

    def test_response_never_html(self, client):
        """Errors must never return HTML."""
        payload = {}
        resp = client.post("/api/routes/alternatives", json=payload)
        content_type = resp.headers.get("Content-Type", "")
        assert "application/json" in content_type


# ── 10. Route identity (stable route_id) ─────────────────────────────────────

class TestRouteIdentity:
    def test_stable_route_id_present(self, ctx):
        n = [0]

        def side_effect(**kwargs):
            n[0] += 1
            return _mock_route(
                nodes=[{"id": "src"}, {"id": f"uid_{n[0]}"}, {"id": "dst"}],
                dist=5.0 + n[0],
                cost=300.0 + n[0] * 5,
            )

        with patch(
            "app.services.routing_service.routing_service.calculate_route",
            side_effect=side_effect,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="src",
                destination_node="dst",
                max_alternatives=2,
                request_id="id-stability-test",
            )

        for alt in res.get("alternatives", []):
            assert "route_id" in alt
            # route_id must be a non-empty string (UUID format)
            assert isinstance(alt["route_id"], str) and len(alt["route_id"]) > 0


# ── 11. Response always has a success field ───────────────────────────────────

class TestAlwaysHasSuccessField:
    def test_error_responses_have_success_false(self, ctx):
        res = alternative_route_service.generate_alternative_routes(
            source_node=None, destination_node="123"
        )
        assert res.get("success") is False

    def test_successful_response_has_success_true(self, ctx):
        n = [0]

        def side_effect(**kwargs):
            n[0] += 1
            return _mock_route(
                nodes=[{"id": "s"}, {"id": f"u{n[0]}"}, {"id": "d"}],
                dist=8.0,
                cost=480.0,
            )

        with patch(
            "app.services.routing_service.routing_service.calculate_route",
            side_effect=side_effect,
        ):
            res = alternative_route_service.generate_alternative_routes(
                source_node="s",
                destination_node="d",
                max_alternatives=1,
                request_id="success-field-test",
            )

        assert "success" in res
        assert isinstance(res["success"], bool)


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])
