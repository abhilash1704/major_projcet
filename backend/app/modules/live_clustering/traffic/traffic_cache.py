"""
Live Clustering — Traffic Mapping Cache
"""
import threading
from typing import Dict, Any, Optional, Tuple

MAX_MAPPING_CACHE_ENTRIES = 500

class TrafficMappingCache:
    def __init__(self, max_entries: int = MAX_MAPPING_CACHE_ENTRIES):
        self._max_entries = max_entries
        self._lock = threading.RLock()
        self._store: Dict[Tuple, Dict[str, Any]] = {}

    @staticmethod
    def _make_key(seg_id: str, lat: float, lon: float) -> Tuple:
        return (str(seg_id), round(float(lat), 4), round(float(lon), 4))

    def get(self, seg_id: str, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        key = self._make_key(seg_id, lat, lon)
        with self._lock:
            return self._store.get(key)

    def set(self, seg_id: str, lat: float, lon: float, value: Dict[str, Any]) -> None:
        key = self._make_key(seg_id, lat, lon)
        with self._lock:
            if len(self._store) >= self._max_entries:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            self._store[key] = value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

mapping_cache = TrafficMappingCache()
