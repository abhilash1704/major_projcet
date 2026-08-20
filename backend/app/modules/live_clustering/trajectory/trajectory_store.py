"""
Bounded In-Memory Trajectory Observation Store
"""
import threading
from typing import Dict, Any, List, Optional
from .schemas import TrajectoryDataset, Observation, GroundTruthVehicle

class TrajectoryStore:
    """
    Thread-safe bounded in-memory store for active trajectory replay datasets
    and observation streams.
    """
    def __init__(self, max_history_observations: int = 5000):
        self._lock = threading.RLock()
        self._max_history = max_history_observations
        
        self._active_dataset: Optional[TrajectoryDataset] = None
        self._ground_truth_map: Dict[str, str] = {}  # user_id -> ground_truth_vehicle_id
        self._observations_by_time: Dict[str, List[Observation]] = {}
        self._sliding_window_buffer: List[Observation] = []
        self._current_timestamp: Optional[str] = None

    def set_dataset(self, dataset: TrajectoryDataset, gt_map: Dict[str, str]) -> None:
        with self._lock:
            self._active_dataset = dataset
            self._ground_truth_map = dict(gt_map)
            self._observations_by_time.clear()
            self._sliding_window_buffer.clear()
            
            for obs in dataset.observations:
                ts = obs.timestamp
                if ts not in self._observations_by_time:
                    self._observations_by_time[ts] = []
                self._observations_by_time[ts].append(obs)

    def get_dataset_summary(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._active_dataset:
                return None
            return self._active_dataset.to_summary_dict()

    def get_ground_truth_map(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._ground_truth_map)

    def get_ground_truth_vehicles(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self._active_dataset:
                return []
            return [v.to_dict() for v in self._active_dataset.vehicles]

    def add_frame_observations(self, timestamp: str, observations: List[Observation]) -> None:
        with self._lock:
            self._current_timestamp = timestamp
            self._sliding_window_buffer.extend(observations)
            
            # Bound sliding window size
            if len(self._sliding_window_buffer) > self._max_history:
                overflow = len(self._sliding_window_buffer) - self._max_history
                self._sliding_window_buffer = self._sliding_window_buffer[overflow:]

    def get_window_observations(self, max_recent: int = 500) -> List[Dict[str, Any]]:
        with self._lock:
            recent = self._sliding_window_buffer[-max_recent:] if self._sliding_window_buffer else []
            return [obs.to_dict() for obs in recent]

    def get_timestamps(self) -> List[str]:
        with self._lock:
            return sorted(list(self._observations_by_time.keys()))

    def get_observations_at_timestamp(self, timestamp: str) -> List[Observation]:
        with self._lock:
            return self._observations_by_time.get(timestamp, [])

    def clear(self) -> None:
        with self._lock:
            self._active_dataset = None
            self._ground_truth_map.clear()
            self._observations_by_time.clear()
            self._sliding_window_buffer.clear()
            self._current_timestamp = None

trajectory_store = TrajectoryStore()
