"""
Traffic Data Service — Sprint 6.1 / 6.5
Provides a read-only snapshot of current live simulated vehicle positions.
Extracts data efficiently from the existing vehicle simulation state without
mutating state, calling routing algorithms, or reloading graphs.
"""
import logging
import math
from datetime import datetime, timezone

from app.modules.vehicle_simulation.services.simulation_store import simulation_store
from app.modules.vehicle_simulation.constants import VEHICLE_STATUS_ACTIVE


class TrafficDataService:
    """
    Read-only service for vehicle position snapshots.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.traffic_intelligence.data")

    def _is_valid_coordinate(self, val: float, min_val: float, max_val: float) -> bool:
        if val is None:
            return False
        try:
            val = float(val)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(val):
            return False
        if not (min_val <= val <= max_val):
            return False
        return True

    def get_active_vehicle_snapshot(self) -> dict:
        """
        Reads all valid, currently active vehicles from the simulation state.
        
        Returns:
            dict with:
                - timestamp (UTC ISO)
                - vehicle_count (int)
                - vehicles (list of dicts)
        """
        logger = self._get_logger()
        
        try:
            # Query the existing simulation state directly from memory.
            snapshot = simulation_store.get_snapshot()
            active_vehicles = [v for v in snapshot.get("vehicles", []) if v.get("status") == VEHICLE_STATUS_ACTIVE]
        except Exception as exc:
            logger.error("Failed to fetch vehicle state: %s", exc)
            raise RuntimeError("Vehicle state unavailable") from exc

        valid_vehicles = []
        for v in active_vehicles:
            lat = v.get("latitude")
            lon = v.get("longitude")
            
            # Filtering: ignore invalid lat/lon
            if not self._is_valid_coordinate(lat, -90.0, 90.0):
                continue
            if not self._is_valid_coordinate(lon, -180.0, 180.0):
                continue
                
            raw_speed = v.get("speed")
            speed = float(raw_speed) if raw_speed is not None and math.isfinite(float(raw_speed)) and float(raw_speed) >= 0 else 0.0

            # Only return lightweight information needed for traffic analysis
            valid_vehicles.append({
                "vehicle_id": v.get("vehicle_id"),
                "latitude": round(float(lat), 8),
                "longitude": round(float(lon), 8),
                "speed_kmh": round(speed, 2),
                "status": v.get("status"),
                "current_node": v.get("current_node"),
                "current_edge": v.get("current_edge")
            })

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "timestamp": timestamp,
            "vehicle_count": len(valid_vehicles),
            "vehicles": valid_vehicles
        }

traffic_data_service = TrafficDataService()
