"""
Unit Test for Live Vehicle Clustering Spatial Isolation (200 Global vs 32 In-Area)
"""
import pytest
from app.modules.vehicle_simulation.services.simulation_store import simulation_store
from app.modules.live_clustering.simulation.vehicle_observation_adapter import vehicle_observation_adapter
from app.modules.live_clustering.clustering.vehicle_cluster_service import vehicle_cluster_service


def test_global_vs_area_vehicle_isolation():
    # Center: Jayanagar 4th Block
    center_lat, center_lon = 12.9250, 77.5938
    radius_meters = 1000.0

    global_vehicles = []
    # 32 vehicles inside Jayanagar radius (~200m to 800m away)
    for i in range(32):
        lat = center_lat + (i % 8) * 0.0008
        lon = center_lon + (i // 8) * 0.0008
        global_vehicles.append({
            "vehicle_id": f"in_area_{i}",
            "latitude": lat,
            "longitude": lon,
            "speed_kmh": 30.0,
            "heading": 90.0,
            "status": "MOVING"
        })

    # 168 vehicles outside (spread across electronic city, whitefield, etc.)
    for i in range(168):
        global_vehicles.append({
            "vehicle_id": f"out_area_{i}",
            "latitude": 12.8399 + (i * 0.001),  # Electronic City
            "longitude": 77.6770 + (i * 0.001),
            "speed_kmh": 40.0,
            "heading": 180.0,
            "status": "MOVING"
        })

    # Populate global simulation store properly
    sim_id = simulation_store.reset_session()
    simulation_store.initialize_vehicles(sim_id, global_vehicles)
    simulation_store.set_status("RUNNING", expected_id=sim_id)

    # Adapter call
    obs_res = vehicle_observation_adapter.get_user_observations_for_area(
        center_lat, center_lon, radius_meters, use_generator_fallback=False
    )

    assert obs_res["total_simulated_vehicles"] == 200
    assert obs_res["vehicles_in_area"] == 32
    assert obs_res["vehicles_after_filter"] == 32

    # Verify DBSCAN receives ONLY in-area observations
    user_obs = obs_res["user_observations"]
    cluster_res = vehicle_cluster_service.compute_vehicle_clusters(user_obs, center_lat, center_lon, radius_meters)

    assert cluster_res["status"] == "ACTIVE"
    for c in cluster_res["clusters"]:
        # Verify cluster centers stay inside 1000m radius
        c_lat, c_lon = c["center_latitude"], c["center_longitude"]
        dlat = (c_lat - center_lat) * 111320.0
        dlon = (c_lon - center_lon) * 111320.0
        dist = (dlat ** 2 + dlon ** 2) ** 0.5
        assert dist <= radius_meters + 10.0  # margin of safety

    # Cleanup
    simulation_store.reset_session()
