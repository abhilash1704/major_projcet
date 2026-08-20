import pytest
import time
from unittest.mock import MagicMock, patch
from flask import Flask

from app.modules.routing.services.alternative_route_service import (
    alternative_route_service,
    _compute_route_similarity,
)


def test_similarity_calculation():
    path1 = ["n1", "n2", "n3", "n4", "n5"]
    path2 = ["n1", "n2", "n3", "n4", "n6"]  # 4/5 overlap = 0.80
    sim = _compute_route_similarity(path1, path2)
    assert round(sim, 2) == 0.80

    path3 = ["n1", "n10", "n11", "n12", "n5"] # 2/5 overlap = 0.40
    sim2 = _compute_route_similarity(path1, path3)
    assert round(sim2, 2) == 0.40


def test_max_two_alternatives_limit():
    with patch("app.services.routing_service.routing_service.calculate_route") as mock_calc:
        # Mock 6 distinct route candidates
        def side_effect(source_node, destination_node, algorithm, routing_mode, reroute_penalties=None):
            penalty_val = sum(reroute_penalties.values()) if reroute_penalties else 0
            unique_id = f"{algorithm}_{penalty_val}"
            return {
                "success": True,
                "distance_km": 10.0 + penalty_val,
                "travel_time_seconds": 600 + penalty_val * 10,
                "traffic_cost": 50.0,
                "total_cost": 650.0 + penalty_val * 10,
                "traffic_level": "LOW",
                "nodes": [{"id": "s"}, {"id": f"via_{unique_id}"}, {"id": "d"}],
                "geometry": [[12.9, 77.5], [12.95, 77.55]],
                "congested_segments": []
            }
        mock_calc.side_effect = side_effect

        res = alternative_route_service.generate_alternative_routes(
            source_node="start_node",
            destination_node="end_node",
            current_route={"path_nodes": ["start_node", "c1", "c2", "end_node"]},
            traffic_level="HIGH",
            max_alternatives=5  # Attempt requesting 5
        )

        assert res.get("success") is True
        alts = res.get("alternatives", [])
        # Must be capped at maximum 2
        assert len(alts) <= 2
        if len(alts) == 2:
            assert alts[0]["color"] == "#22c55e"  # Green
            assert alts[1]["color"] == "#3b82f6"  # Blue


def test_duplicate_route_filtering():
    with patch("app.services.routing_service.routing_service.calculate_route") as mock_calc:
        # Return identical node paths for all workers
        mock_calc.return_value = {
            "success": True,
            "distance_km": 10.0,
            "travel_time_seconds": 600,
            "traffic_cost": 50.0,
            "total_cost": 650.0,
            "traffic_level": "LOW",
            "nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}, {"id": "n4"}],
            "geometry": [],
            "congested_segments": []
        }

        # Current route is identical to candidates
        res = alternative_route_service.generate_alternative_routes(
            source_node="n1",
            destination_node="n4",
            current_route={"path_nodes": ["n1", "n2", "n3", "n4"]},
            traffic_level="HIGH"
        )

        # All candidates are 100% duplicate of current route (sim=1.0 >= 0.80 threshold)
        assert res.get("success") is True
        assert len(res.get("alternatives", [])) == 0
        assert "No suitable alternative" in res.get("message", "")


def test_timeout_protection():
    with patch("app.services.routing_service.routing_service.calculate_route") as mock_calc:
        def slow_calc(*args, **kwargs):
            time.sleep(2)
            return {"success": False}
        mock_calc.side_effect = slow_calc

        with patch("app.modules.routing.services.alternative_route_service.AlternativeRouteService._execute_candidate_generation") as mock_exec:
            mock_exec.return_value = {
                "success": False,
                "status": "error",
                "reason": "timeout",
                "message": "Alternative route calculation timed out.",
                "current_route": {},
                "alternatives": []
            }
            t0 = time.time()
            res = alternative_route_service.generate_alternative_routes(
                source_node="n1",
                destination_node="n2",
                traffic_level="HIGH"
            )
            elapsed = time.time() - t0

            assert elapsed < 5.0
            assert res.get("success") is False
            assert res.get("reason") == "timeout"



if __name__ == "__main__":
    pytest.main(["-v", __file__])
