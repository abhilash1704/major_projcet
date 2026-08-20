"""
Traffic Hotspot Service — Sprint 6.4 / Sprint 8

Analyzes DBSCAN clusters to detect significant traffic hotspots,
assign severities, and rank them by score.
Computes an authoritative global_traffic_level from detected hotspots.
"""
import logging
from flask import current_app

from .dbscan_service import dbscan_service


class TrafficHotspotService:
    """
    Evaluates traffic clusters to find true hotspots based on eligibility rules.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.traffic_intelligence.hotspot")

    def _get_config(self, key: str, default: float | int):
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            return default

    def detect_hotspots(self) -> dict:
        """
        Fetches current clusters and computes hotspots.
        Returns authoritative global_traffic_level.
        """
        logger = self._get_logger()
        
        # Get clusters from DBSCAN service
        cluster_response = dbscan_service.get_clusters()
        
        clusters = cluster_response.get("clusters", [])
        if not clusters:
            return {
                "success": True,
                "timestamp": cluster_response.get("timestamp"),
                "vehicle_count": cluster_response.get("vehicle_count", 0),
                "cluster_count": cluster_response.get("cluster_count", 0),
                "hotspot_count": 0,
                "hotspots": [],
                "global_traffic_level": "N/A",
                "noise_vehicle_count": cluster_response.get("noise_vehicle_count", 0),
            }
            
        # Hotspot thresholds (all from config for easy tuning)
        min_vehicles = self._get_config('HOTSPOT_MIN_VEHICLES', 3)
        min_density  = self._get_config('HOTSPOT_MIN_DENSITY', 5.0)
        max_avg_speed = self._get_config('HOTSPOT_MAX_AVERAGE_SPEED', 80.0)
        low_threshold  = self._get_config('HOTSPOT_LOW_THRESHOLD', 0.25)
        high_threshold = self._get_config('HOTSPOT_HIGH_THRESHOLD', 0.60)

        # Normalisation ceilings — tuned to route-based simulation densities
        MAX_EXPECTED_VEHICLES = self._get_config('HOTSPOT_MAX_EXPECTED_VEHICLES', 80.0)
        MAX_EXPECTED_DENSITY  = self._get_config('HOTSPOT_MAX_EXPECTED_DENSITY', 80.0)
        MAX_SPEED_LIMIT = 80.0
        
        hotspots = []
        high_count = 0
        med_count  = 0
        low_count  = 0
        
        for cluster in clusters:
            count   = cluster["vehicle_count"]
            density = cluster["density_vehicles_per_km2"]
            speed   = cluster["average_speed_kmh"]
            
            # 1. Eligibility Check
            is_eligible = (
                count   >= min_vehicles and
                density >= min_density  and
                speed   <= max_avg_speed
            )
            
            if not is_eligible:
                continue
                
            # 2. Normalisation & Scoring
            count_score   = min(1.0, count   / MAX_EXPECTED_VEHICLES)
            density_score = min(1.0, density / MAX_EXPECTED_DENSITY)
            # Inverse speed: lower speed → higher congestion
            speed_score = 1.0 - min(1.0, speed / MAX_SPEED_LIMIT)
            
            # Weighted combination (density primary, speed secondary, count tertiary)
            hotspot_score = round(0.45 * density_score + 0.30 * speed_score + 0.25 * count_score, 2)
            
            # 3. Severity Classification
            if hotspot_score >= high_threshold:
                severity = "HIGH"
                high_count += 1
            elif hotspot_score >= low_threshold:
                severity = "MEDIUM"
                med_count += 1
            else:
                severity = "LOW"
                low_count += 1
                
            hotspots.append({
                "hotspot_id":               f"hotspot_{cluster['cluster_id']}",
                "cluster_id":               cluster["cluster_id"],
                "center_latitude":          cluster["center_latitude"],
                "center_longitude":         cluster["center_longitude"],
                "vehicle_count":            count,
                "density_vehicles_per_km2": density,
                "average_speed_kmh":        speed,
                "radius_meters":            cluster["radius_meters"],
                "severity":                 severity,
                "hotspot_score":            hotspot_score,
            })
            
        # 4. Sort highest score first
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)
        
        # 5. Derive authoritative global traffic level
        if high_count > 0:
            global_level = "HIGH"
        elif med_count > 0:
            global_level = "MEDIUM"
        elif low_count > 0:
            global_level = "LOW"
        elif clusters:
            # Clusters exist but none qualified as hotspots yet (all LOW density)
            global_level = "LOW"
        else:
            global_level = "N/A"
        
        logger.info(
            "Vehicles: %d | Clusters: %d | Hotspots: %d | High: %d | Medium: %d | Low: %d | Global: %s",
            cluster_response.get("vehicle_count", 0),
            len(clusters),
            len(hotspots),
            high_count, med_count, low_count, global_level
        )
                    
        return {
            "success":              True,
            "timestamp":            cluster_response.get("timestamp"),
            "vehicle_count":        cluster_response.get("vehicle_count", 0),
            "cluster_count":        len(clusters),
            "noise_vehicle_count":  cluster_response.get("noise_vehicle_count", 0),
            "hotspot_count":        len(hotspots),
            "hotspots":             hotspots,
            "global_traffic_level": global_level,
        }

hotspot_service = TrafficHotspotService()
