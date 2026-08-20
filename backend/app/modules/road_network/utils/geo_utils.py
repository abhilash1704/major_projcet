import math
from ..constants import EARTH_RADIUS_KM

def is_valid_coordinate(latitude, longitude):
    """
    Validates whether latitude and longitude are within standard geographical ranges.
    - Latitude: -90.0 to 90.0
    - Longitude: -180.0 to 180.0
    """
    if latitude is None or longitude is None:
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    except (ValueError, TypeError):
        return False

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on Earth in kilometers
    using the Haversine formula.
    """
    if not is_valid_coordinate(lat1, lon1) or not is_valid_coordinate(lat2, lon2):
        raise ValueError("Invalid coordinates provided to haversine_distance")

    lat1_rad, lon1_rad = math.radians(float(lat1)), math.radians(float(lon1))
    lat2_rad, lon2_rad = math.radians(float(lat2)), math.radians(float(lon2))

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c

def bounding_box_contains(lat, lon, bbox):
    """
    Checks if a coordinate (lat, lon) is within a bounding box dictionary.
    bbox expected shape: {'min_lat': float, 'max_lat': float, 'min_lng': float, 'max_lng': float}
    """
    if not is_valid_coordinate(lat, lon):
        return False
    if not isinstance(bbox, dict):
        return False

    min_lat = bbox.get('min_lat', -90.0)
    max_lat = bbox.get('max_lat', 90.0)
    min_lng = bbox.get('min_lng', -180.0)
    max_lng = bbox.get('max_lng', 180.0)

    return min_lat <= float(lat) <= max_lat and min_lng <= float(lon) <= max_lng

def calculate_travel_time(distance_km, speed_kmh):
    """
    Calculates travel time in seconds given distance in km and speed in km/h.
    Returns 0.0 if speed <= 0.
    """
    if distance_km is None or speed_kmh is None or speed_kmh <= 0:
        return 0.0
    
    # hours = distance / speed -> seconds = hours * 3600
    hours = float(distance_km) / float(speed_kmh)
    return round(hours * 3600.0, 2)


def compute_region_bbox(lat1, lon1, lat2=None, lon2=None, padding_deg=0.08, min_span_deg=0.12):
    """
    Computes a bounding box covering point 1 (and optional point 2) with a padding margin.
    Ensures minimum width/height so Overpass queries return sufficient road context.
    """
    lats = [float(lat1)]
    lons = [float(lon1)]

    if lat2 is not None and lon2 is not None and is_valid_coordinate(lat2, lon2):
        lats.append(float(lat2))
        lons.append(float(lon2))

    min_lat = min(lats) - padding_deg
    max_lat = max(lats) + padding_deg
    min_lng = min(lons) - padding_deg
    max_lng = max(lons) + padding_deg

    # Enforce minimum span
    if (max_lat - min_lat) < min_span_deg:
        mid_lat = (min_lat + max_lat) / 2.0
        min_lat = mid_lat - (min_span_deg / 2.0)
        max_lat = mid_lat + (min_span_deg / 2.0)

    if (max_lng - min_lng) < min_span_deg:
        mid_lng = (min_lng + max_lng) / 2.0
        min_lng = mid_lng - (min_span_deg / 2.0)
        max_lng = mid_lng + (min_span_deg / 2.0)

    return {
        'min_lat': round(min_lat, 4),
        'max_lat': round(max_lat, 4),
        'min_lng': round(min_lng, 4),
        'max_lng': round(max_lng, 4)
    }


def generate_region_cache_key(bbox):
    """
    Generates a deterministic region cache key string for disk serialization.
    Example: region_15.0500_15.3500_76.3000_77.0000 -> region_lat1505_lat1535_lon7630_lon7700
    """
    if not isinstance(bbox, dict):
        return "region_default"

    min_lat = int(round(bbox.get('min_lat', 0.0) * 100))
    max_lat = int(round(bbox.get('max_lat', 0.0) * 100))
    min_lng = int(round(bbox.get('min_lng', 0.0) * 100))
    max_lng = int(round(bbox.get('max_lng', 0.0) * 100))

    return f"region_lat{min_lat}_{max_lat}_lon{min_lng}_{max_lng}"


def get_graph_bbox(nx_graph):
    """
    Calculates the exact min/max lat/lon bounds of all nodes in a NetworkX graph.
    Returns None if graph is empty.
    """
    if nx_graph is None or len(nx_graph) == 0:
        return None

    lats = []
    lons = []
    for n, data in nx_graph.nodes(data=True):
        lat = data.get('lat', data.get('y'))
        lon = data.get('lon', data.get('x'))
        if lat is not None and lon is not None:
            lats.append(float(lat))
            lons.append(float(lon))

    if not lats or not lons:
        return None

    return {
        'min_lat': min(lats),
        'max_lat': max(lats),
        'min_lng': min(lons),
        'max_lng': max(lons)
    }

