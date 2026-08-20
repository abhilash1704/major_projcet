import os

# Module metadata
MODULE_NAME = "road-network"
MODULE_VERSION = "1.0.0"

# OpenStreetMap & Graph Configuration
OSM_PROVIDER_DEFAULT_URL = os.environ.get('OSM_PROVIDER_URL', 'https://overpass-api.de/api/interpreter')
GRAPH_CACHE_DIR = os.environ.get('GRAPH_CACHE_DIR', 'instance/graph_cache')
MAX_GRAPH_NODES = int(os.environ.get('MAX_GRAPH_NODES', '100000'))

DEFAULT_SEARCH_RADIUS_KM = 5.0
MAX_SNAP_DISTANCE_KM = float(os.environ.get('MAX_SNAP_DISTANCE_KM', '10.0'))  # Maximum allowed snapping distance in kilometers
DEFAULT_PADDING_DEG = 0.08  # Bounding box expansion margin (~9km padding)
EARTH_RADIUS_KM = 6371.0  # Earth's mean radius in kilometers

# Default geographic area (Bangalore Metropolitan Region bounding box)
DEFAULT_GEO_BOUNDS = {
    'min_lat': 12.8000,
    'max_lat': 13.1500,
    'min_lng': 77.4000,
    'max_lng': 77.7500
}

# Road type default speed limits (km/h) for future travel time calculations
DEFAULT_SPEED_LIMITS = {
    'motorway': 100.0,
    'trunk': 80.0,
    'primary': 60.0,
    'secondary': 50.0,
    'tertiary': 40.0,
    'residential': 30.0,
    'unclassified': 30.0,
    'default': 40.0
}
