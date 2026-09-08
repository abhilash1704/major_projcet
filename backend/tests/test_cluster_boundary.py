"""
Unit Test for Cluster Boundary Validation
"""
import pytest
from app.modules.live_clustering.spatial_filter import filter_clusters_to_analysis_area, haversine_distance_meters


def test_cluster_center_outside_radius_is_discarded():
    center_lat, center_lon = 12.9174, 77.6228
    radius_meters = 1000.0

    # Cluster inside (center 500m away)
    cluster_in = {
        "cluster_id": "cluster_01",
        "center_latitude": center_lat + (500.0 / 111320.0),
        "center_longitude": center_lon,
        "user_count": 3
    }

    # Cluster center outside (center 1200m away)
    cluster_out = {
        "cluster_id": "cluster_02",
        "center_latitude": center_lat + (1200.0 / 111320.0),
        "center_longitude": center_lon,
        "user_count": 4
    }

    clusters = [cluster_in, cluster_out]
    filtered = filter_clusters_to_analysis_area(clusters, center_lat, center_lon, radius_meters)

    assert len(filtered) == 1
    assert filtered[0]["cluster_id"] == "cluster_01"
    dist = haversine_distance_meters(center_lat, center_lon, filtered[0]["center_latitude"], filtered[0]["center_longitude"])
    assert dist <= radius_meters
