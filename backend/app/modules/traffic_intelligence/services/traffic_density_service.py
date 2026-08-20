"""
Traffic Density Service — Sprint 6.2

Calculates spatial density of simulated vehicles.
Uses a configurable meter-based grid to aggregate vehicle counts and calculate density (vehicles/km^2).
"""
import logging
import math
from typing import Dict, List, Any

from .traffic_data_service import traffic_data_service


class TrafficDensityService:
    """
    Computes spatial density metrics for active vehicles.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.traffic_intelligence.density")

    def _classify_density(self, vehicle_count: int) -> str:
        """Classify cell density based on configurable thresholds."""
        # Configurable thresholds could be injected from app.config
        # For now, using standard safe defaults as requested.
        LOW_THRESHOLD = 10
        HIGH_THRESHOLD = 30
        
        if vehicle_count < LOW_THRESHOLD:
            return "LOW"
        elif vehicle_count < HIGH_THRESHOLD:
            return "MEDIUM"
        else:
            return "HIGH"

    def calculate_density(self, cell_size_meters: int = 500) -> dict:
        """
        Retrieves the active vehicle snapshot and calculates spatial density grid.
        
        Args:
            cell_size_meters: size of each grid cell edge in meters.
            
        Returns:
            dict containing cell count, vehicle count, and list of occupied cells.
        """
        logger = self._get_logger()
        
        if cell_size_meters <= 0:
            raise ValueError("cell_size_meters must be a positive integer.")
            
        # 1. Obtain current vehicle snapshot
        snapshot = traffic_data_service.get_active_vehicle_snapshot()
        vehicles = snapshot.get("vehicles", [])
        
        if not vehicles:
            return {
                "timestamp": snapshot.get("timestamp"),
                "vehicle_count": 0,
                "cell_count": 0,
                "cell_size_meters": cell_size_meters,
                "cells": []
            }

        # 2. Compute geographic cells O(N)
        # Using a flat dict to accumulate data per cell
        cells: Dict[str, Dict[str, Any]] = {}
        
        # Area in km^2
        area_km2 = (cell_size_meters / 1000.0) ** 2
        
        for v in vehicles:
            lat = v["latitude"]
            lon = v["longitude"]
            speed = v["speed_kmh"]
            
            # Meter-based projection (equirectangular approximation)
            lat_rad = math.radians(lat)
            # 1 degree of latitude is approximately 111,000 meters
            meters_per_degree_lat = 111000.0
            # 1 degree of longitude is approximately 111,000 * cos(lat) meters
            meters_per_degree_lon = 111000.0 * math.cos(lat_rad)
            
            cell_x = int(math.floor((lon * meters_per_degree_lon) / cell_size_meters))
            cell_y = int(math.floor((lat * meters_per_degree_lat) / cell_size_meters))
            
            cell_id = f"cell_{cell_x}_{cell_y}"
            
            if cell_id not in cells:
                # Calculate center coordinates for the cell
                center_lat = ((cell_y + 0.5) * cell_size_meters) / meters_per_degree_lat
                center_lon = ((cell_x + 0.5) * cell_size_meters) / meters_per_degree_lon
                
                cells[cell_id] = {
                    "cell_id": cell_id,
                    "center_latitude": round(center_lat, 6),
                    "center_longitude": round(center_lon, 6),
                    "vehicle_count": 0,
                    "area_km2": area_km2,
                    "total_speed": 0.0,
                    "valid_speed_count": 0
                }
                
            cells[cell_id]["vehicle_count"] += 1
            if speed > 0.0:
                cells[cell_id]["total_speed"] += speed
                cells[cell_id]["valid_speed_count"] += 1

        # 3. Finalize density metrics
        final_cells = []
        for cell_id, data in cells.items():
            count = data["vehicle_count"]
            density = count / area_km2
            
            avg_speed = 0.0
            if data["valid_speed_count"] > 0:
                avg_speed = data["total_speed"] / data["valid_speed_count"]
                
            density_level = self._classify_density(count)
            
            final_cells.append({
                "cell_id": cell_id,
                "center_latitude": data["center_latitude"],
                "center_longitude": data["center_longitude"],
                "vehicle_count": count,
                "area_km2": round(area_km2, 6),
                "density_vehicles_per_km2": round(density, 2),
                "average_speed_kmh": round(avg_speed, 2),
                "density_level": density_level
            })
            
        logger.info("Density calculated: %d vehicles, %d cells (size: %dm)", 
                    len(vehicles), len(final_cells), cell_size_meters)

        return {
            "timestamp": snapshot.get("timestamp"),
            "vehicle_count": len(vehicles),
            "cell_count": len(final_cells),
            "cell_size_meters": cell_size_meters,
            "cells": final_cells
        }

traffic_density_service = TrafficDensityService()
