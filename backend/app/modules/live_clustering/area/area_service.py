"""
Live Clustering — Area Service
"""
import math
from typing import List, Dict, Any
from .monitoring_areas import MONITORING_AREAS

_AREA_BY_ID: Dict[str, Dict[str, Any]] = {a["id"]: a for a in MONITORING_AREAS}


def get_all_areas() -> List[Dict[str, Any]]:
    """Return full list of monitoring areas."""
    return MONITORING_AREAS


def get_area_by_id(area_id: str) -> Dict[str, Any] | None:
    """Return a single area by id, or None."""
    return _AREA_BY_ID.get(area_id)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two (lat, lon) points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def filter_users_in_area(
    users: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_m: float,
) -> List[Dict[str, Any]]:
    """
    Returns the subset of items within radius_m of (center_lat, center_lon).
    """
    if not users:
        return []

    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * math.cos(math.radians(center_lat)))

    lat_min = center_lat - dlat
    lat_max = center_lat + dlat
    lon_min = center_lon - dlon
    lon_max = center_lon + dlon

    result = []
    for u in users:
        lat = u.get("latitude")
        lon = u.get("longitude")
        if lat is None or lon is None:
            continue
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            continue
        if _haversine_m(center_lat, center_lon, lat, lon) <= radius_m:
            result.append(u)

    return result
