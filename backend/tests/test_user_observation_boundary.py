"""
Unit Test for User Observation Spatial Boundary Screening
"""
import pytest
from app.modules.live_clustering.spatial_filter import filter_observations_to_analysis_area


def test_noisy_user_observation_outside_radius_is_discarded():
    center_lat, center_lon = 12.9174, 77.6228
    radius_meters = 1000.0

    # User observation 1: inside (400m away)
    obs_inside = {
        "observation_id": "obs_1",
        "user_id": "u1",
        "latitude": 12.9190,
        "longitude": 77.6228,
        "speed_kmh": 25.0
    }

    # User observation 2: noisy GPS probe pushed to 1500m away
    obs_noisy_outside = {
        "observation_id": "obs_2",
        "user_id": "u2",
        "latitude": center_lat + (1500.0 / 111320.0),
        "longitude": center_lon,
        "speed_kmh": 25.0
    }

    observations = [obs_inside, obs_noisy_outside]
    filtered = filter_observations_to_analysis_area(observations, center_lat, center_lon, radius_meters)

    assert len(filtered) == 1
    assert filtered[0]["observation_id"] == "obs_1"
