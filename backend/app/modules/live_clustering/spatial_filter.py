"""
Centralized Spatial Filtering Engine for Live Vehicle Clustering

Strict 2-stage spatial isolation using exact Haversine geographic distance.
"""
import math
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("routeflow.live_clustering.spatial_filter")

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes exact Haversine geographic distance in meters between two lat/lon coordinates.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_METERS * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def filter_vehicles_to_analysis_area(
    vehicles: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> List[Dict[str, Any]]:
    """
    SHARED BACKEND FUNCTION (Requirement 6):
    Filters vehicles strictly inside radius_meters of (center_lat, center_lon).
    
    STAGE 1: Bounding box candidate screening.
    STAGE 2: Exact Haversine distance validation (dist <= radius_meters).
    """
    if not vehicles:
        return []

    # Stage 1: Bounding box pre-filter
    dlat = radius_meters / 111320.0
    cos_lat = math.cos(math.radians(center_lat))
    dlon = radius_meters / (111320.0 * (cos_lat if abs(cos_lat) > 1e-6 else 1.0))

    lat_min, lat_max = center_lat - dlat, center_lat + dlat
    lon_min, lon_max = center_lon - dlon, center_lon + dlon

    filtered_vehicles = []
    for v in vehicles:
        try:
            v_lat = float(v.get("latitude", 0.0))
            v_lon = float(v.get("longitude", 0.0))

            # Stage 1 check
            if not (lat_min <= v_lat <= lat_max and lon_min <= v_lon <= lon_max):
                continue

            # Stage 2 exact Haversine check
            dist = haversine_distance_meters(center_lat, center_lon, v_lat, v_lon)
            if dist <= radius_meters:
                filtered_vehicles.append(v)
        except (ValueError, TypeError):
            continue

    return filtered_vehicles


def filter_observations_to_analysis_area(
    observations: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> List[Dict[str, Any]]:
    """
    Filters GPS user observations strictly inside radius_meters of (center_lat, center_lon).
    (Requirement 7: Noisy GPS observations pushed outside the circle are discarded).
    """
    if not observations:
        return []

    dlat = radius_meters / 111320.0
    cos_lat = math.cos(math.radians(center_lat))
    dlon = radius_meters / (111320.0 * (cos_lat if abs(cos_lat) > 1e-6 else 1.0))

    lat_min, lat_max = center_lat - dlat, center_lat + dlat
    lon_min, lon_max = center_lon - dlon, center_lon + dlon

    valid_obs = []
    for obs in observations:
        try:
            lat = float(obs.get("latitude", 0.0))
            lon = float(obs.get("longitude", 0.0))

            if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                continue

            dist = haversine_distance_meters(center_lat, center_lon, lat, lon)
            if dist <= radius_meters:
                valid_obs.append(obs)
        except (ValueError, TypeError):
            continue

    return valid_obs


def filter_clusters_to_analysis_area(
    clusters: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> List[Dict[str, Any]]:
    """
    Filters DBSCAN clusters to ensure cluster centers are strictly within radius_meters.
    (Requirement 9: Safety validation).
    """
    if not clusters:
        return []

    valid_clusters = []
    for c in clusters:
        try:
            c_lat = float(c.get("center_latitude", 0.0))
            c_lon = float(c.get("center_longitude", 0.0))

            dist = haversine_distance_meters(center_lat, center_lon, c_lat, c_lon)
            if dist <= radius_meters:
                valid_clusters.append(c)
        except (ValueError, TypeError):
            continue

    return valid_clusters


def filter_roads_to_analysis_area(
    road_segments: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> List[Dict[str, Any]]:
    """
    Filters road density segments to those physically within radius_meters of area center.
    (Requirement 10: Area-bounded road density).
    """
    if not road_segments:
        return []

    valid_segments = []
    for seg in road_segments:
        geometry = seg.get("geometry") or seg.get("coordinates") or []
        if not geometry:
            continue

        # Check if any coordinate point of the segment falls within radius_meters
        is_inside = False
        for pt in geometry:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                p_lat, p_lon = float(pt[0]), float(pt[1])
                if haversine_distance_meters(center_lat, center_lon, p_lat, p_lon) <= radius_meters:
                    is_inside = True
                    break

        if is_inside:
            valid_segments.append(seg)

    return valid_segments
