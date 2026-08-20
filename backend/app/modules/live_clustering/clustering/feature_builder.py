"""
Observation Feature Vector Builder for DBSCAN Clustering
"""
import math
import numpy as np
from typing import List, Dict, Any, Tuple

def _lat_lon_to_meters(lat: float, lon: float, ref_lat: float, ref_lon: float) -> Tuple[float, float]:
    """Converts (lat, lon) to local Cartesian (x, y) meters relative to ref point."""
    lat_rad = math.radians(ref_lat)
    cos_lat = math.cos(lat_rad)
    m_per_deg_lat = 111132.92
    m_per_deg_lon = 111412.84 * cos_lat

    x = (lon - ref_lon) * m_per_deg_lon
    y = (lat - ref_lat) * m_per_deg_lat
    return x, y


class FeatureBuilder:
    """
    Constructs normalized spatial-temporal feature matrices for DBSCAN vehicle clustering.
    Ground truth vehicle IDs are STRICTLY EXCLUDED.
    """
    
    def build_feature_matrix(
        self,
        observations: List[Dict[str, Any]],
        ref_lat: float,
        ref_lon: float,
        speed_weight: float = 0.5,
        heading_weight: float = 0.2,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Builds feature matrix of shape (N, 4):
          - Col 0: local_x (meters)
          - Col 1: local_y (meters)
          - Col 2: speed_kmh * speed_weight
          - Col 3: heading_radians * heading_weight
          
        Returns:
            Tuple of (feature_matrix, valid_observations)
        """
        if not observations:
            return np.empty((0, 4)), []
            
        valid_obs = []
        features = []
        
        for obs in observations:
            lat = obs.get("latitude")
            lon = obs.get("longitude")
            if lat is None or lon is None:
                continue
                
            try:
                lat = float(lat)
                lon = float(lon)
                speed = float(obs.get("speed_kmh", 0.0))
                heading = float(obs.get("heading", 0.0))
            except (ValueError, TypeError):
                continue
                
            x, y = _lat_lon_to_meters(lat, lon, ref_lat, ref_lon)
            h_rad = math.radians(heading)
            
            features.append([
                x,
                y,
                speed * speed_weight,
                math.sin(h_rad) * heading_weight * 10.0, # Directional component
            ])
            valid_obs.append(obs)
            
        if not features:
            return np.empty((0, 4)), []
            
        return np.array(features, dtype=float), valid_obs


feature_builder = FeatureBuilder()
