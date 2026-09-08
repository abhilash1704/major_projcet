"""
Clock-Driven Trajectory Replay Engine

NOTE: This engine replays SYNTHETIC multi-vehicle trajectory datasets for validation and
ground-truth scoring (via evaluation_engine). It is NOT a live data source.
"""
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from .trajectory_store import trajectory_store
from .schemas import TrajectoryDataset, Observation

logger = logging.getLogger("routeflow.live_clustering.trajectory.replay_engine")


class TrajectoryReplayEngine:
    """
    Clock-driven streaming replay engine for vehicle trajectory datasets.
    
    Supported States: IDLE, READY, RUNNING, PAUSED, STOPPED, ERROR
    Supported Speeds: 1.0 (1x), 5.0 (5x), 10.0 (10x)
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._status: str = "IDLE"
        self._speed_multiplier: float = 1.0
        
        self._timestamps: List[str] = []
        self._current_index: int = 0
        
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set() # Unpaused by default
        
        self._latest_snapshot: Dict[str, Any] = {
            "status": "IDLE",
            "speed": 1.0,
            "current_index": 0,
            "total_frames": 0,
            "current_timestamp": None,
            "observations": [],
        }

    def load_dataset(self, dataset: TrajectoryDataset, gt_map: Dict[str, str]) -> Dict[str, Any]:
        """Loads a generated trajectory dataset into the replay engine."""
        with self._lock:
            self.stop()
            trajectory_store.set_dataset(dataset, gt_map)
            self._timestamps = trajectory_store.get_timestamps()
            self._current_index = 0
            self._status = "READY"
            
            self._update_snapshot([], None)
            logger.info("[ReplayEngine] Loaded dataset '%s' with %d frames", dataset.dataset_id, len(self._timestamps))
            return self.get_status()

    def set_speed(self, multiplier: float) -> Dict[str, Any]:
        with self._lock:
            if multiplier not in [1.0, 2.0, 5.0, 10.0]:
                multiplier = 1.0
            self._speed_multiplier = multiplier
            logger.info("[ReplayEngine] Replay speed updated to %.1fx", multiplier)
            return self.get_status()

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if not self._timestamps:
                self._status = "ERROR"
                return self.get_status()
                
            if self._status in ["READY", "PAUSED", "STOPPED"]:
                self._status = "RUNNING"
                self._pause_event.set()
                self._stop_event.clear()
                
                if self._worker_thread is not None and self._worker_thread.is_alive():
                    self._worker_thread.join(timeout=0.5)

                if self._worker_thread is None or not self._worker_thread.is_alive():
                    self._worker_thread = threading.Thread(
                        target=self._replay_loop,
                        name="TrajectoryReplayWorker",
                        daemon=True
                    )
                    self._worker_thread.start()
                    
            return self.get_status()

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            if self._status == "RUNNING":
                self._status = "PAUSED"
                self._pause_event.clear()
            return self.get_status()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self._status = "STOPPED"
            self._stop_event.set()
            self._pause_event.set()
            self._current_index = 0
            self._update_snapshot([], None)
        if self._worker_thread is not None and self._worker_thread.is_alive():
            if threading.current_thread() != self._worker_thread:
                self._worker_thread.join(timeout=1.0)
        return self.get_status()

    def _replay_loop(self) -> None:
        """Background thread step loop."""
        logger.info("[ReplayEngine] Replay loop started.")
        
        while not self._stop_event.is_set():
            self._pause_event.wait()
            
            if self._stop_event.is_set():
                break
                
            with self._lock:
                if self._current_index >= len(self._timestamps):
                    self._status = "STOPPED"
                    logger.info("[ReplayEngine] Replay completed all frames.")
                    break
                    
                timestamp = self._timestamps[self._current_index]
                obs_list = trajectory_store.get_observations_at_timestamp(timestamp)
                
                # Push frame to store
                trajectory_store.add_frame_observations(timestamp, obs_list)
                
                # Update snapshot
                obs_dicts = [o.to_dict() for o in obs_list]
                self._update_snapshot(obs_dicts, timestamp)
                
                self._current_index += 1
                speed = self._speed_multiplier
                
            # Base tick sleep (1 second / speed multiplier)
            sleep_duration = max(0.05, 1.0 / speed)
            time.sleep(sleep_duration)

    def _update_snapshot(self, observations: List[Dict[str, Any]], timestamp: Optional[str]) -> None:
        self._latest_snapshot = {
            "status": self._status,
            "speed": self._speed_multiplier,
            "current_index": self._current_index,
            "total_frames": len(self._timestamps),
            "current_timestamp": timestamp,
            "observations": observations,
            "dataset": trajectory_store.get_dataset_summary(),
        }

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            # Refresh observations with sliding window if running
            snap = dict(self._latest_snapshot)
            snap["status"] = self._status
            snap["window_observations"] = trajectory_store.get_window_observations(max_recent=300)
            return snap

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "speed": self._speed_multiplier,
                "current_index": self._current_index,
                "total_frames": len(self._timestamps),
                "dataset": trajectory_store.get_dataset_summary(),
            }


replay_engine = TrajectoryReplayEngine()
