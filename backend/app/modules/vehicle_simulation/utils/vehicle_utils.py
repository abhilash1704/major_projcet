"""
Vehicle Utilities — Sprint 4.1 / 4.2

Geographic utility functions for the vehicle simulation engine.
Reuses math patterns consistent with the existing road_network geo_utils.
"""
import math


def calculate_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial compass bearing from point A to point B.

    Returns a value in degrees [0, 360).
    0° = North, 90° = East, 180° = South, 270° = West.

    Args:
        lat1, lon1: Source node coordinates (degrees)
        lat2, lon2: Destination node coordinates (degrees)

    Returns:
        float: Bearing in degrees [0, 360)
    """
    lat1_r = math.radians(float(lat1))
    lat2_r = math.radians(float(lat2))
    dlon   = math.radians(float(lon2) - float(lon1))

    x = math.sin(dlon) * math.cos(lat2_r)
    y = (
        math.cos(lat1_r) * math.sin(lat2_r)
        - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


def interpolate_position(
    src_lat: float,
    src_lon: float,
    dst_lat: float,
    dst_lon: float,
    fraction: float,
) -> tuple[float, float]:
    """
    Linearly interpolate a point that lies ``fraction`` of the way
    from (src_lat, src_lon) to (dst_lat, dst_lon).

    Args:
        src_lat, src_lon: Source node coordinates
        dst_lat, dst_lon: Destination node coordinates
        fraction: Value in [0, 1] — 0 = at source, 1 = at destination

    Returns:
        (latitude, longitude) tuple representing the interpolated position
    """
    fraction = max(0.0, min(1.0, float(fraction)))
    lat = src_lat + fraction * (dst_lat - src_lat)
    lon = src_lon + fraction * (dst_lon - src_lon)
    return lat, lon
