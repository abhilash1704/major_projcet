"""
User Observation Generator for Live Vehicle Clustering

Generates multiple virtual GPS user observations for each simulated vehicle
with realistic spatial offsets, speed/heading variations, and ground-truth labeling.
"""
import math
import random
import uuid
import time
from typing import Dict, Any, List, Optional
from app.modules.live_clustering.config import (
    MIN_USERS_PER_VEHICLE,
    MAX_USERS_PER_VEHICLE,
    GPS_NOISE_RADIUS_METERS,
)

USER_ID_SUFFIXES = ["A", "B", "C", "D", "E", "F"]

def offset_lat_lon(lat: float, lon: float, dx_meters: float, dy_meters: float) -> tuple[float, float]:
    """
    Applies small metric offsets (dx_meters, dy_meters) to a lat/lon coordinate.
    """
    lat_rad = math.radians(lat)
    delta_lat = dy_meters / 111000.0
    delta_lon = dx_meters / (111000.0 * math.cos(lat_rad) + 1e-9)
    return lat + delta_lat, lon + delta_lon


def generate_user_observations_for_vehicle(
    vehicle: Dict[str, Any],
    user_count: Optional[int] = None,
    noise_radius_m: float = GPS_NOISE_RADIUS_METERS,
    timestamp_str: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates multiple virtual user GPS observations for a single simulated vehicle.
    
    IMPORTANT:
    vehicle_source_id is for GROUND TRUTH EVALUATION ONLY.
    It MUST NOT be passed into the DBSCAN clustering algorithm.
    """
    vehicle_id = str(vehicle.get("vehicle_id", "v_unknown"))
    center_lat = float(vehicle.get("latitude", 0.0))
    center_lon = float(vehicle.get("longitude", 0.0))
    base_speed = float(vehicle.get("speed_kmh", vehicle.get("speed", 25.0)))
    base_heading = float(vehicle.get("heading", 0.0))
    edge_id = vehicle.get("current_edge") or vehicle.get("road_edge_id")

    if user_count is None:
        # Deterministic per vehicle_id or random controlled count
        seed_val = sum(ord(c) for c in vehicle_id)
        rng = random.Random(seed_val + int(time.time() // 10))
        user_count = rng.randint(MIN_USERS_PER_VEHICLE, MAX_USERS_PER_VEHICLE)

    user_count = max(1, user_count)
    observations = []
    ts = timestamp_str or vehicle.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for i in range(user_count):
        suffix = USER_ID_SUFFIXES[i % len(USER_ID_SUFFIXES)]
        user_id = f"U_{vehicle_id}_{suffix}"
        
        # Spatial noise inside offset circle
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0.5, noise_radius_m)
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        
        obs_lat, obs_lon = offset_lat_lon(center_lat, center_lon, dx, dy)
        
        # Speed & heading jitter
        obs_speed = max(0.0, base_speed + random.uniform(-0.5, 0.5))
        obs_heading = (base_heading + random.uniform(-2.0, 2.0)) % 360.0
        accuracy = round(random.uniform(3.0, 8.0), 1)

        obs = {
            "observation_id": f"obs_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "vehicle_source_id": vehicle_id,  # GROUND TRUTH ONLY
            "timestamp": ts,
            "latitude": round(obs_lat, 6),
            "longitude": round(obs_lon, 6),
            "speed_kmh": round(obs_speed, 1),
            "heading": round(obs_heading, 1),
            "accuracy_m": accuracy,
            "road_edge_id": edge_id,
        }
        observations.append(obs)

    return observations
