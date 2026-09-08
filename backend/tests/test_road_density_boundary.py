"""
Unit Test for Road Density Boundary Validation
"""
import pytest
from app.modules.live_clustering.spatial_filter import filter_roads_to_analysis_area, haversine_distance_meters


def test_road_density_restricted_to_analysis_area():
    center_lat, center_lon = 12.9174, 77.6228
    radius_meters = 1000.0

    # Road inside radius (~300m away)
    road_inside = {
        "road_edge_id": "road_in_1",
        "road_name": "Silk Board Main Road",
        "density_level": "HIGH",
        "geometry": [
            [center_lat + 0.002, center_lon + 0.002],
            [center_lat + 0.003, center_lon + 0.003]
        ]
    }

    # Road outside radius (~3000m away)
    road_outside = {
        "road_edge_id": "road_out_1",
        "road_name": "Indiranagar 100ft Road",
        "density_level": "HIGH",
        "geometry": [
            [12.9719, 77.6412],
            [12.9730, 77.6420]
        ]
    }

    roads = [road_inside, road_outside]
    filtered = filter_roads_to_analysis_area(roads, center_lat, center_lon, radius_meters)

    assert len(filtered) == 1
    assert filtered[0]["road_edge_id"] == "road_in_1"
