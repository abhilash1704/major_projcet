"""
Live Clustering Configuration Module
"""
import os

# Spatial and Trajectory Parameters
DEFAULT_ANALYSIS_RADIUS_METERS: float = float(os.environ.get("DEFAULT_ANALYSIS_RADIUS_METERS", 1000.0))
GPS_NOISE_METERS: float = float(os.environ.get("GPS_NOISE_METERS", 5.0))
USER_POSITION_JITTER_METERS: float = float(os.environ.get("USER_POSITION_JITTER_METERS", 3.0))

# Multi-User per Vehicle Parameters
MIN_USERS_PER_VEHICLE: int = int(os.environ.get("MIN_USERS_PER_VEHICLE", 1))
MAX_USERS_PER_VEHICLE: int = int(os.environ.get("MAX_USERS_PER_VEHICLE", 4))
GPS_NOISE_RADIUS_METERS: float = float(os.environ.get("GPS_NOISE_RADIUS_METERS", 12.0))

# Clustering Parameters (DBSCAN)
# eps in meters for spatial distance
CLUSTER_EPS_METERS: float = float(os.environ.get("CLUSTER_EPS_METERS", 25.0))
CLUSTER_MIN_SAMPLES: int = int(os.environ.get("CLUSTER_MIN_SAMPLES", 2))
DBSCAN_EPS_METERS: float = CLUSTER_EPS_METERS
DBSCAN_MIN_SAMPLES: int = CLUSTER_MIN_SAMPLES

# Temporal window for snapshot observations (seconds)
CLUSTERING_WINDOW_SECONDS: float = float(os.environ.get("CLUSTERING_WINDOW_SECONDS", 5.0))
CLUSTER_TIME_WINDOW_SECONDS: float = CLUSTERING_WINDOW_SECONDS

# Road Density Thresholds (vehicles per edge)
LOW_DENSITY_MAX: int = int(os.environ.get("LOW_DENSITY_MAX", 3))
HIGH_DENSITY_MIN: int = int(os.environ.get("HIGH_DENSITY_MIN", 8))

# Mapping match threshold
TRAFFIC_EDGE_MATCH_DISTANCE_METERS: float = float(os.environ.get("TRAFFIC_EDGE_MATCH_DISTANCE_METERS", 50.0))

# External Real Traffic Freshness
FRESH_TTL_SECONDS: int = int(os.environ.get("TRAFFIC_FRESH_TTL_SECONDS", 60))
STALE_TTL_SECONDS: int = int(os.environ.get("TRAFFIC_STALE_TTL_SECONDS", 300))
MAX_CACHE_ENTRIES: int = int(os.environ.get("TRAFFIC_MAX_CACHE_ENTRIES", 200))

