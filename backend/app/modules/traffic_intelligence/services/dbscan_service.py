"""
Traffic DBSCAN Service — Sprint 6.3 / Sprint 8

Calculates spatial clusters using DBSCAN from scikit-learn.
Operates on the existing live simulated vehicle position data.

Sprint 8 additions:
- clustered_vehicle_count exposed in response
- per-cluster density_level (LOW/MEDIUM/HIGH) added for ClusterLayer visualization
"""
import logging
import math
import time
from datetime import datetime, timezone
import numpy as np
from sklearn.cluster import DBSCAN
from flask import current_app

from .traffic_data_service import traffic_data_service


class TrafficClusterService:
    """
    Computes traffic clusters using DBSCAN.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.traffic_intelligence.dbscan")

    def _get_config(self, key: str, default: int | float):
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            return default

    def _classify_cluster_density(self, density: float) -> str:
        """Single authoritative classification function.
        Thresholds tuned to route-based simulation densities (5–200 veh/km²).
        """
        # Use config if available, else sensible defaults
        try:
            low_density  = current_app.config.get('HOTSPOT_MIN_DENSITY', 5.0)
            high_density = current_app.config.get('HOTSPOT_MAX_EXPECTED_DENSITY', 80.0) * 0.75
        except RuntimeError:
            low_density  = 5.0
            high_density = 60.0
        
        if density >= high_density:
            return "HIGH"
        elif density >= low_density:
            return "MEDIUM"
        else:
            return "LOW"

    def get_clusters(self) -> dict:
        """
        Retrieves the active vehicle snapshot and calculates DBSCAN spatial clusters.
        
        Returns:
            dict containing cluster count, noise count, clustered_vehicle_count,
            and cluster details with per-cluster density_level.
        """
        logger = self._get_logger()
        t_start = time.perf_counter()
        
        # Configurations
        eps_meters  = self._get_config('DBSCAN_EPS_METERS', 200)
        min_samples = self._get_config('DBSCAN_MIN_SAMPLES', 3)

        # 1. Obtain current vehicle snapshot
        snapshot = traffic_data_service.get_active_vehicle_snapshot()
        vehicles  = snapshot.get("vehicles", [])
        timestamp = snapshot.get("timestamp")

        if not vehicles:
            return {
                "success": True,
                "timestamp": timestamp,
                "vehicle_count": 0,
                "cluster_count": 0,
                "clustered_vehicle_count": 0,
                "noise_vehicle_count": 0,
                "processing_time_ms": 0,
                "clusters": []
            }
            
        if len(vehicles) < min_samples:
            return {
                "success": True,
                "timestamp": timestamp,
                "vehicle_count": len(vehicles),
                "cluster_count": 0,
                "clustered_vehicle_count": 0,
                "noise_vehicle_count": len(vehicles),
                "processing_time_ms": 0,
                "clusters": []
            }

        # 2. Extract valid coords and convert to local metric coordinate space
        lats = [v["latitude"]  for v in vehicles]
        lons = [v["longitude"] for v in vehicles]
        
        mean_lat = sum(lats) / len(lats)
        mean_lat_rad = math.radians(mean_lat)
        meters_per_degree_lat = 111000.0
        meters_per_degree_lon = 111000.0 * math.cos(mean_lat_rad)
        
        X = np.zeros((len(vehicles), 2))
        for i in range(len(vehicles)):
            X[i, 0] = lons[i] * meters_per_degree_lon
            X[i, 1] = lats[i] * meters_per_degree_lat

        # 3. Run DBSCAN with metric='euclidean' on local metric space
        db = DBSCAN(eps=eps_meters, min_samples=min_samples, metric='euclidean').fit(X)
        labels = db.labels_

        # 4. Aggregate clusters (label -1 = noise)
        cluster_groups: dict[int, dict] = {}
        noise_count = 0

        for i, label in enumerate(labels):
            if label == -1:
                noise_count += 1
                continue
                
            cluster_id = int(label)
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = {
                    "cluster_id": cluster_id,
                    "vehicles":   [],
                    "x_list":     [],
                    "y_list":     []
                }
            cluster_groups[cluster_id]["vehicles"].append(vehicles[i])
            cluster_groups[cluster_id]["x_list"].append(X[i, 0])
            cluster_groups[cluster_id]["y_list"].append(X[i, 1])

        # 5. Compute metrics for each cluster
        final_clusters = []
        total_clustered = 0

        for cluster_id, group in cluster_groups.items():
            cluster_vehicles = group["vehicles"]
            x_list = group["x_list"]
            y_list = group["y_list"]
            count  = len(cluster_vehicles)
            total_clustered += count
            
            # Centroid
            center_x = sum(x_list) / count
            center_y = sum(y_list) / count
            
            # Convert centroid back to lat/lon
            center_lat = center_y / meters_per_degree_lat
            center_lon = center_x / meters_per_degree_lon
            
            # Max distance from centroid for radius
            max_sq_dist = 0.0
            for i in range(count):
                dx = x_list[i] - center_x
                dy = y_list[i] - center_y
                max_sq_dist = max(max_sq_dist, dx * dx + dy * dy)
            radius_meters = math.sqrt(max_sq_dist)
            
            # Density: vehicles / cluster_area
            # Minimum effective radius of 10m to avoid division by zero on tiny clusters
            eff_radius_m = max(radius_meters, 10.0)
            area_km2 = math.pi * (eff_radius_m / 1000.0) ** 2
            density  = count / area_km2
            
            # Average speed
            total_speed = 0.0
            valid_speed_count = 0
            for v in cluster_vehicles:
                speed = v.get("speed_kmh", 0.0)
                if speed > 0.0:
                    total_speed += speed
                    valid_speed_count += 1
            avg_speed = round(total_speed / valid_speed_count, 2) if valid_speed_count > 0 else 0.0
            
            # Single-source severity classification
            density_level = self._classify_cluster_density(density)

            vehicle_ids = [v["vehicle_id"] for v in cluster_vehicles]
            
            final_clusters.append({
                "cluster_id":               cluster_id,
                "vehicle_count":            count,
                "center_latitude":          round(center_lat, 6),
                "center_longitude":         round(center_lon, 6),
                "average_speed_kmh":        avg_speed,
                "radius_meters":            round(radius_meters, 1),
                "density_vehicles_per_km2": round(density, 2),
                "density_level":            density_level,
                "vehicle_ids":              vehicle_ids,
            })
            
        t_end = time.perf_counter()
        processing_ms = round((t_end - t_start) * 1000, 1)

        logger.info(
            "DBSCAN [eps=%dm, min=%d]: Vehicles=%d | Clusters=%d | Clustered=%d | Noise=%d | Time=%.1fms",
            eps_meters, min_samples,
            len(vehicles), len(final_clusters), total_clustered, noise_count, processing_ms
        )

        return {
            "success":                True,
            "timestamp":              timestamp,
            "vehicle_count":          len(vehicles),
            "cluster_count":          len(final_clusters),
            "clustered_vehicle_count": total_clustered,
            "noise_vehicle_count":    noise_count,
            "processing_time_ms":     processing_ms,
            "clusters":               final_clusters,
        }

dbscan_service = TrafficClusterService()
