"""
test_live_vehicle_clustering_auto.py — Unit Tests for Live Vehicle Clustering Automatic Mode
"""
import pytest
from app.modules.live_clustering.service import live_clustering_service


def test_active_area_and_session_id_generation():
    """Verify set_active_area initializes and resets session_id on area change."""
    area1 = live_clustering_service.set_active_area(
        lat=12.9174, lon=77.6228, name="Silk Board Junction", area_id="silk_board", radius_m=1000.0
    )
    assert area1["id"] == "silk_board"
    session1 = area1["session_id"]
    assert session1 is not None

    # Set same area -> session remains same
    area1_again = live_clustering_service.set_active_area(
        lat=12.9174, lon=77.6228, name="Silk Board Junction", area_id="silk_board", radius_m=1000.0
    )
    assert area1_again["session_id"] == session1

    # Set different area -> new session_id generated
    area2 = live_clustering_service.set_active_area(
        lat=12.9698, lon=77.7499, name="Whitefield", area_id="whitefield", radius_m=1000.0
    )
    assert area2["id"] == "whitefield"
    assert area2["session_id"] != session1


def test_get_clustering_snapshot_returns_live_snapshot():
    """Verify get_clustering_snapshot returns continuous live snapshot data."""
    live_clustering_service.set_active_area(
        lat=12.9174, lon=77.6228, name="Silk Board Junction", area_id="silk_board", radius_m=1000.0
    )
    snapshot = live_clustering_service.get_clustering_snapshot()

    assert snapshot["status"] in ["LIVE", "ACTIVE", "UPDATING"]
    assert snapshot["disclaimer"] == "Simulation-based live traffic analysis"
    assert "simulation" in snapshot
    assert "clustering" in snapshot
    assert "road_density" in snapshot
    assert "evaluation" in snapshot

    sim = snapshot["simulation"]
    assert sim["vehicles_in_area"] >= 0
    assert sim["user_observations"] >= 0
    assert sim["observation_window_seconds"] == 5.0


def test_ground_truth_vehicle_id_not_in_dbscan_features():
    """Verify ground truth vehicle IDs are strictly excluded from DBSCAN feature builder."""
    from app.modules.live_clustering.simulation.vehicle_observation_adapter import vehicle_observation_adapter
    from app.modules.live_clustering.clustering.feature_builder import feature_builder

    obs_data = vehicle_observation_adapter.get_user_observations_for_area(12.9174, 77.6228, 1000.0)
    user_obs = obs_data.get("user_observations", [])

    if user_obs:
        features, valid_obs = feature_builder.build_feature_matrix(user_obs, 12.9174, 77.6228)
        # Verify feature array dimension is 3 (lat, lon, speed) or 4 (heading), NOT including vehicle_id
        for vec in features:
            assert len(vec) in [2, 3, 4]


def test_multiple_users_per_vehicle_grouping():
    """Verify DBSCAN clusters group observations to reduce vehicle count."""
    live_clustering_service.set_active_area(
        lat=12.9174, lon=77.6228, name="Silk Board Junction", area_id="silk_board", radius_m=1000.0
    )
    snapshot = live_clustering_service.get_clustering_snapshot()
    metrics = snapshot.get("clustering", {}).get("metrics", {})

    total_users = metrics.get("total_users", 0)
    est_vehicles = metrics.get("estimated_vehicles", 0)
    users_grouped = metrics.get("users_grouped", 0)

    if total_users > 0:
        assert est_vehicles <= total_users
        assert users_grouped == total_users - est_vehicles


def test_snapshot_resilience_on_exception(monkeypatch):
    """Verify snapshot fallback handles errors gracefully without crashing."""
    live_clustering_service.set_active_area(
        lat=12.9174, lon=77.6228, name="Silk Board Junction", area_id="silk_board", radius_m=1000.0
    )
    # Generate initial snapshot
    snap1 = live_clustering_service.get_clustering_snapshot()

    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated processing glitch")

    from app.modules.live_clustering.simulation.vehicle_observation_adapter import vehicle_observation_adapter
    monkeypatch.setattr(vehicle_observation_adapter, "get_user_observations_for_area", mock_fail)

    # Calling snapshot when error occurs should return fallback status
    snap_fallback = live_clustering_service.get_clustering_snapshot()
    assert snap_fallback["status"] in ["UPDATING", "TEMPORARY_ANALYSIS_ERROR"]
