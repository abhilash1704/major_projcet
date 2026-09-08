"""
Unit Tests for Analysis Area Filter & Spatial Isolation
"""
import pytest
from app.modules.live_clustering.spatial_filter import (
    haversine_distance_meters,
    filter_vehicles_to_analysis_area,
    filter_observations_to_analysis_area,
)
from app.modules.live_clustering.service import live_clustering_service


def test_vehicle_inside_outside_radius():
    center_lat, center_lon = 12.9174, 77.6228  # Silk Board
    radius_meters = 1000.0

    # Vehicle inside (~200m away)
    v_inside = {"vehicle_id": "v1", "latitude": 12.9190, "longitude": 77.6228}
    # Vehicle outside (~2.5km away in Indiranagar)
    v_outside = {"vehicle_id": "v2", "latitude": 12.9719, "longitude": 77.6412}

    vehicles = [v_inside, v_outside]
    filtered = filter_vehicles_to_analysis_area(vehicles, center_lat, center_lon, radius_meters)

    assert len(filtered) == 1
    assert filtered[0]["vehicle_id"] == "v1"


def test_boundary_condition():
    center_lat, center_lon = 12.9174, 77.6228
    radius_meters = 1000.0

    # Calculate coordinate at almost exact 1000m
    # 1 deg lat = ~111,320m -> 1000m = 0.0089828 deg lat
    lat_exact = center_lat + (1000.0 / 111320.0)
    v_boundary = {"vehicle_id": "v_bound", "latitude": lat_exact, "longitude": center_lon}

    dist = haversine_distance_meters(center_lat, center_lon, lat_exact, center_lon)
    filtered = filter_vehicles_to_analysis_area([v_boundary], center_lat, center_lon, radius_meters)

    if dist <= radius_meters:
        assert len(filtered) == 1
    else:
        assert len(filtered) == 0


def test_radius_scaling():
    center_lat, center_lon = 12.9174, 77.6228
    # Vehicle at ~800m distance
    lat_800m = center_lat + (800.0 / 111320.0)
    v_800m = {"vehicle_id": "v_800", "latitude": lat_800m, "longitude": center_lon}

    # At 500m radius -> excluded
    filtered_500 = filter_vehicles_to_analysis_area([v_800m], center_lat, center_lon, 500.0)
    assert len(filtered_500) == 0

    # At 1000m radius -> included
    filtered_1000 = filter_vehicles_to_analysis_area([v_800m], center_lat, center_lon, 1000.0)
    assert len(filtered_1000) == 1

    # At 2000m radius -> included
    filtered_2000 = filter_vehicles_to_analysis_area([v_800m], center_lat, center_lon, 2000.0)
    assert len(filtered_2000) == 1


def test_area_change_session_reset():
    # Set area 1 (Silk Board)
    area1 = live_clustering_service.set_active_area(12.9174, 77.6228, name="Silk Board", radius_m=1000.0)
    session1 = area1["session_id"]

    # Set area 2 (Whitefield)
    area2 = live_clustering_service.set_active_area(12.9698, 77.7500, name="Whitefield", radius_m=1000.0)
    session2 = area2["session_id"]

    # Sessions must be different and new session starts clean
    assert session1 != session2
    assert area2["generation"] == 0


def test_browser_gps_has_zero_effect():
    """
    Verifies that backend filtering depends strictly on selected area coordinates
    and ignores any hypothetical browser GPS or user device location.
    """
    selected_lat, selected_lon = 12.9174, 77.6228
    browser_gps_lat, browser_gps_lon = 13.0827, 80.2707  # Chennai (unrelated)

    v_inside_selected = {"vehicle_id": "v_selected", "latitude": 12.9180, "longitude": 77.6228}
    v_inside_browser = {"vehicle_id": "v_browser", "latitude": 13.0830, "longitude": 80.2707}

    filtered = filter_vehicles_to_analysis_area(
        [v_inside_selected, v_inside_browser], selected_lat, selected_lon, 1000.0
    )

    assert len(filtered) == 1
    assert filtered[0]["vehicle_id"] == "v_selected"
