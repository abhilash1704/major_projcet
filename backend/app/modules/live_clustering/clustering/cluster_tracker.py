"""
Cluster Identity Tracking Service
"""
import math
import threading
from typing import Dict, List, Any, Optional

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


class ClusterTracker:
    """
    Maintains persistent cluster identifiers across sequential replay snapshots.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._counter = 0
        self._previous_clusters: Dict[str, Dict[str, Any]] = {}

    def _next_id(self) -> str:
        self._counter += 1
        return f"vcluster_{self._counter:03d}"

    def reset(self) -> None:
        with self._lock:
            self._previous_clusters.clear()
            self._counter = 0

    def match_or_create_id(
        self,
        user_ids: List[str],
        center_lat: float,
        center_lon: float,
        max_dist_m: float = 35.0
    ) -> str:
        with self._lock:
            new_set = set(user_ids)
            best_id = None
            best_jaccard = 0.0
            min_dist = float("inf")

            for cid, prev in self._previous_clusters.items():
                prev_set = set(prev.get("user_ids", []))
                intersection = new_set.intersection(prev_set)
                union = new_set.union(prev_set)

                if union:
                    jaccard = len(intersection) / len(union)
                    if jaccard > best_jaccard:
                        best_jaccard = jaccard
                        best_id = cid

                if best_jaccard == 0.0:
                    dist = _haversine_m(center_lat, center_lon, prev["center_lat"], prev["center_lon"])
                    if dist <= max_dist_m and dist < min_dist:
                        min_dist = dist
                        best_id = cid

            if best_jaccard > 0.0 or min_dist <= max_dist_m:
                return best_id or self._next_id()

            return self._next_id()

    def update_registry(self, current_clusters: List[Dict[str, Any]]) -> None:
        with self._lock:
            new_prev = {}
            for clus in current_clusters:
                cid = clus["cluster_id"]
                new_prev[cid] = {
                    "cluster_id": cid,
                    "user_ids": clus.get("user_ids", []),
                    "center_lat": clus.get("center_latitude", 0.0),
                    "center_lon": clus.get("center_longitude", 0.0),
                }
            self._previous_clusters = new_prev


cluster_tracker = ClusterTracker()
