import logging
import threading
import uuid
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("routeflow.vehicle_simulation.store")

class SimulationStore:
    """
    In-memory state store for vehicle simulation.
    Acts as the single source of truth for live simulation data to prevent
    high-frequency SQLite contention (StaleDataError).
    """

    def __init__(self):
        self._lock = threading.RLock()
        
        # Core state
        self._simulation_id: Optional[str] = None
        self._status: str = "IDLE"  # IDLE, GENERATING, READY, RUNNING, PAUSED, STOPPED, ERROR
        self._vehicles: Dict[str, Dict[str, Any]] = {}
        
        # Snapshot persistence
        self._last_snapshot_time: float = 0.0
        self._snapshot_interval_seconds: float = 5.0

    @property
    def simulation_id(self) -> Optional[str]:
        with self._lock:
            return self._simulation_id

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def vehicles(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return self._vehicles

    @property
    def last_snapshot_time(self) -> float:
        with self._lock:
            return self._last_snapshot_time

    def set_last_snapshot_time(self, t: float):
        with self._lock:
            self._last_snapshot_time = t

    def get_vehicle_count(self) -> int:
        with self._lock:
            return len(self._vehicles)

    # ── Lifecycle methods ──────────────────────────────────────────────────────
    
    def reset_session(self) -> str:
        """
        Clears all in-memory data, stops simulation, and generates a new session ID.
        Returns the new simulation_id.
        """
        with self._lock:
            self._vehicles.clear()
            self._status = "IDLE"
            self._last_snapshot_time = 0.0
            new_id = f"sim_{uuid.uuid4().hex}"
            self._simulation_id = new_id
            logger.info("Simulation session reset. New ID: %s", new_id)
            return new_id

    def clear(self) -> str:
        """Alias for reset_session."""
        return self.reset_session()

    def set_status(self, new_status: str, expected_id: Optional[str] = None):
        """
        Sets the simulation status.
        If expected_id is provided, it validates that the ID matches.
        """
        valid_statuses = {"IDLE", "GENERATING", "READY", "RUNNING", "PAUSED", "STOPPED", "ERROR"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")

        with self._lock:
            if expected_id and expected_id != self._simulation_id:
                raise ValueError(
                    f"Session mismatch. Expected {self._simulation_id}, got {expected_id}."
                )
            logger.info("Simulation status transition: %s -> %s", self._status, new_status)
            self._status = new_status

    def initialize_vehicles(self, sim_id: str, vehicles_list: list[Dict[str, Any]]):
        """
        Initializes the in-memory vehicle dictionary for the session.
        """
        with self._lock:
            if sim_id != self._simulation_id:
                raise ValueError("Session ID mismatch during vehicle initialization.")
            
            self._vehicles.clear()
            for v in vehicles_list:
                # Store vehicle state locally
                vehicle_data = dict(v)
                vehicle_data["simulation_id"] = sim_id
                self._vehicles[v["vehicle_id"]] = vehicle_data
            
            logger.info("Initialized %d vehicles in memory for session %s", len(vehicles_list), sim_id)

    def update_vehicle(self, sim_id: str, vehicle_id: str, updates: Dict[str, Any]):
        """
        Update a specific vehicle's state.
        """
        with self._lock:
            if sim_id != self._simulation_id:
                return  # Silent ignore for stale workers
            if vehicle_id in self._vehicles:
                self._vehicles[vehicle_id].update(updates)

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Returns a read-only snapshot of all vehicles for APIs.
        """
        with self._lock:
            vehicles_copy = list(self._vehicles.values())
            return {
                "simulation_id": self._simulation_id,
                "status": self._status,
                "count": len(vehicles_copy),
                "vehicles": vehicles_copy
            }

simulation_store = SimulationStore()
