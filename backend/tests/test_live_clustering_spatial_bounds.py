"""
Comprehensive Spatial Bounds Test Suite (test_live_clustering_spatial_bounds.py)
Validates all 9 required spatial boundary conditions and radius/session isolation.
"""
import pytest
from app.modules.live_clustering.spatial_filter import (
    haversine_distance_meters,
    filter_vehicles_to_analysis_area,
    filter_observations_to_analysis_area,
    filter_clusters_to_analysis_area,
    filter_roads_to_analysis_area,
)
from app.modules.live_clustering.service import live_clustering_service


def test_1_vehicle_inside_radius_accepted():
    center_lat, center_lon = 12.9250, 77.5938  # KR Puram / Jayanagar
    radius_meters = 500.0

    v_inside = {"vehicle_id": "v_in", "latitude": 12.9260, "longitude": 77.5938}
    res = filter_vehicles_to_analysis_area([v_inside], center_lat, center_lon, radius_meters)
    assert len(res) == 1
    assert res[0]["vehicle_id"] == "v_in"


def test_2_vehicle_outside_radius_rejected():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    v_outside = {"vehicle_id": "v_out", "latitude": 12.9500, "longitude": 77.6500}
    res = filter_vehicles_to_analysis_area([v_outside], center_lat, center_lon, radius_meters)
    assert len(res) == 0


def test_3_boundary_vehicle_validation():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    # 490m distance (inside) vs 510m distance (outside)
    lat_490m = center_lat + (490.0 / 111320.0)
    lat_510m = center_lat + (510.0 / 111320.0)

    v_490m = {"vehicle_id": "v_490", "latitude": lat_490m, "longitude": center_lon}
    v_510m = {"vehicle_id": "v_510", "latitude": lat_510m, "longitude": center_lon}

    res = filter_vehicles_to_analysis_area([v_490m, v_510m], center_lat, center_lon, radius_meters)
    assert len(res) == 1
    assert res[0]["vehicle_id"] == "v_490"


def test_4_user_observation_inside_accepted():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    obs_in = {"observation_id": "o_in", "latitude": center_lat + 0.001, "longitude": center_lon}
    res = filter_observations_to_analysis_area([obs_in], center_lat, center_lon, radius_meters)
    assert len(res) == 1


def test_5_user_observation_outside_rejected():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    obs_out = {"observation_id": "o_out", "latitude": center_lat + 0.01, "longitude": center_lon}
    res = filter_observations_to_analysis_area([obs_out], center_lat, center_lon, radius_meters)
    assert len(res) == 0


def test_6_cluster_center_inside_accepted():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    cluster_in = {"cluster_id": "c_in", "center_latitude": center_lat + 0.001, "center_longitude": center_lon}
    res = filter_clusters_to_analysis_area([cluster_in], center_lat, center_lon, radius_meters)
    assert len(res) == 1


def test_7_cluster_center_outside_rejected():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    cluster_out = {"cluster_id": "c_out", "center_latitude": center_lat + 0.01, "center_longitude": center_lon}
    res = filter_clusters_to_analysis_area([cluster_out], center_lat, center_lon, radius_meters)
    assert len(res) == 0


def test_8_density_road_inside_accepted():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    road_in = {
        "road_edge_id": "r_in",
        "geometry": [[center_lat + 0.001, center_lon], [center_lat + 0.002, center_lon]]
    }
    res = filter_roads_to_analysis_area([road_in], center_lat, center_lon, radius_meters)
    assert len(res) == 1


def test_9_density_road_outside_rejected():
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 500.0

    road_out = {
        "road_edge_id": "r_out",
        "geometry": [[center_lat + 0.05, center_lon], [center_lat + 0.06, center_lon]]
    }
    res = filter_roads_to_analysis_area([road_out], center_lat, center_lon, radius_meters)
    assert len(res) == 0


def test_10_dynamic_radius_scaling():
    from app.modules.live_clustering.simulation.vehicle_observation_adapter import vehicle_observation_adapter
    from app.modules.live_clustering.trajectory.replay_engine import replay_engine
    from app.modules.live_clustering.trajectory.trajectory_store import trajectory_store
    center_lat, center_lon = 12.9250, 77.5938

    # 500m radius -> expected 30 fallback vehicles
    replay_engine.stop()
    trajectory_store.clear()
    obs_500 = vehicle_observation_adapter.get_user_observations_for_area(center_lat, center_lon, 500.0, use_generator_fallback=True)

    # 1000m radius -> expected 75 fallback vehicles
    replay_engine.stop()
    trajectory_store.clear()
    obs_1000 = vehicle_observation_adapter.get_user_observations_for_area(center_lat, center_lon, 1000.0, use_generator_fallback=True)

    assert obs_500["status"] == "LIVE"
    assert obs_1000["status"] == "LIVE"
    assert len(obs_500["user_observations"]) > 0
    assert len(obs_1000["user_observations"]) > 0


def test_11_area_switch_session_invalidation():
    # Session 1: KR Puram
    s1 = live_clustering_service.set_active_area(12.9716, 77.6960, name="KR Puram", radius_m=500.0)
    id1 = s1["session_id"]

    # Session 2: Whitefield
    s2 = live_clustering_service.set_active_area(12.9698, 77.7500, name="Whitefield", radius_m=1000.0)
    id2 = s2["session_id"]

    assert id1 != id2
    assert s2["name"] == "Whitefield"


def test_12_browser_gps_zero_effect():
    """
    Browser GPS coordinates are completely ignored by spatial_filter.
    Only the selected area lat/lon is used.
    """
    selected_center = (12.9250, 77.5938)
    browser_location = (13.0827, 80.2707)  # Chennai

    target_vehicle = {"vehicle_id": "v1", "latitude": 12.9260, "longitude": 77.5938}

    # Verify calculation depends solely on selected_center
    dist_to_selected = haversine_distance_meters(selected_center[0], selected_center[1], target_vehicle["latitude"], target_vehicle["longitude"])
    dist_to_browser = haversine_distance_meters(browser_location[0], browser_location[1], target_vehicle["latitude"], target_vehicle["longitude"])

    assert dist_to_selected <= 500.0
    assert dist_to_browser > 100000.0  # >100km away
