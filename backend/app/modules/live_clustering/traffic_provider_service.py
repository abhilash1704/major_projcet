"""
Live Clustering — Traffic Provider Service (Phase 5: Real External Traffic)

Isolated external traffic integration layer for Live Clustering area analysis.

Supported Providers (via environment variables):
  - LIVE_TRAFFIC_PROVIDER = "tomtom" | "here" | "openrouteservice"
  - LIVE_TRAFFIC_API_KEY  = "<API_KEY>"

Features:
  1. Real HTTP adapter for TomTom / HERE / OpenRouteService Traffic Flow APIs.
  2. Safe unconfigured behavior:
     - No key/provider -> status = UNAVAILABLE, provider = NOT_CONFIGURED
     - HTTP failure     -> status = UNAVAILABLE, provider = ERROR
  3. Bounded in-memory cache with FRESHNESS tracking:
     - Age <= 60s  -> provider_status = LIVE
     - Age <= 300s -> provider_status = STALE
     - Age > 300s  -> Expired (re-fetches or returns UNAVAILABLE)
  4. Standardized normalization model including segments and speed metrics.

NO connection to RouteFlow routing graph, edge weights, or vehicle simulation.
"""
import logging
import os
import time
import json
import urllib.request
import urllib.parse
import threading
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("routeflow.live_clustering.traffic_provider")

# ---------------------------------------------------------------------------
# Configuration & Environment Variables
# ---------------------------------------------------------------------------
FRESH_TTL_SECONDS: int = int(os.environ.get("TRAFFIC_FRESH_TTL_SECONDS", 60))
STALE_TTL_SECONDS: int = int(os.environ.get("TRAFFIC_STALE_TTL_SECONDS", 300))
MAX_CACHE_ENTRIES: int = int(os.environ.get("TRAFFIC_MAX_CACHE_ENTRIES", 200))


def _get_provider_name() -> str:
    return os.environ.get("LIVE_TRAFFIC_PROVIDER", "").strip().lower()


def _get_api_key() -> str:
    return os.environ.get("LIVE_TRAFFIC_API_KEY", "").strip()


# ---------------------------------------------------------------------------
# Standard Internal Response Formatter
# ---------------------------------------------------------------------------

def _unavailable_response(reason: str) -> Dict[str, Any]:
    """
    Returns an UNAVAILABLE response dict.
    reason: "NOT_CONFIGURED" | "ERROR"
    """
    provider_name = _get_provider_name() or "none"
    data_state = f"UNAVAILABLE/{reason}"
    logger.info("[TrafficProvider] Data state: %s (provider_name=%s)", data_state, provider_name)
    return {
        "source":              "REAL_TRAFFIC_PROVIDER",
        "status":              "UNAVAILABLE",
        "data_state":          data_state,
        "congestion_level":    None,
        "current_speed_kmh":   None,
        "free_flow_speed_kmh": None,
        "provider":            reason,          # "NOT_CONFIGURED" | "ERROR"
        "provider_name":       provider_name,
        "provider_status":     "UNAVAILABLE",
        "timestamp":           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cached":              False,
        "segments":            [],
    }


def _build_normalized_response(
    status: str,                    # "LOW" | "MEDIUM" | "HIGH"
    congestion_level: Optional[float],
    current_speed_kmh: Optional[float],
    free_flow_speed_kmh: Optional[float],
    segments: List[Dict[str, Any]],
    raw: Dict[str, Any],
    provider_status: str = "LIVE",   # "LIVE" | "STALE"
    cached: bool = False,
    fetched_at: Optional[float] = None,
) -> Dict[str, Any]:
    provider_name = _get_provider_name() or "real_provider"
    data_state = f"REAL/{provider_status}"
    timestamp_str = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(fetched_at if fetched_at else time.time())
    )
    logger.info("[TrafficProvider] Data state: %s (provider_name=%s, cached=%s, segments=%d)", data_state, provider_name, cached, len(segments))
    return {
        "source":              "REAL_TRAFFIC_PROVIDER",
        "status":              status,
        "data_state":          data_state,
        "congestion_level":    congestion_level,
        "current_speed_kmh":   current_speed_kmh,
        "free_flow_speed_kmh": free_flow_speed_kmh,
        "provider":            "REAL",
        "provider_name":       provider_name,
        "provider_status":     provider_status,  # "LIVE" | "STALE"
        "timestamp":           timestamp_str,
        "cached":              cached,
        "segments":            segments,
        "raw":                 raw,
    }


# ---------------------------------------------------------------------------
# Real External API Adapters
# ---------------------------------------------------------------------------

def _fetch_tomtom_flow(lat: float, lon: float, key: str) -> Optional[Dict[str, Any]]:
    """
    TomTom Traffic Flow Segment Data API.
    URL: https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={key}&point={lat},{lon}
    """
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={urllib.parse.quote(key)}&point={lat},{lon}"
    req = urllib.request.Request(url, headers={"User-Agent": "RouteFlow-LiveClustering/1.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode("utf-8"))
    return None


def _fetch_here_flow(lat: float, lon: float, key: str) -> Optional[Dict[str, Any]]:
    """
    HERE Traffic Flow API v7.
    """
    url = f"https://traffic.ls.hereapi.com/traffic/6.0/flow.json?apiKey={urllib.parse.quote(key)}&prox={lat},{lon},1000"
    req = urllib.request.Request(url, headers={"User-Agent": "RouteFlow-LiveClustering/1.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode("utf-8"))
    return None


def _fetch_from_provider(lat: float, lon: float, radius_m: float) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Invokes configured external provider API.
    Returns (raw_dict, success_flag).
    """
    provider_name = _get_provider_name()
    api_key = _get_api_key()

    if not provider_name or not api_key:
        return None, False

    try:
        if provider_name == "tomtom":
            data = _fetch_tomtom_flow(lat, lon, api_key)
            return data, data is not None
        elif provider_name == "here":
            data = _fetch_here_flow(lat, lon, api_key)
            return data, data is not None
        else:
            logger.warning("[TrafficProvider] Unsupported provider: %s", provider_name)
            return None, False
    except Exception as exc:
        logger.error("[TrafficProvider] External fetch failed for %s: %s", provider_name, exc)
        return None, False


def _normalize_provider_data(raw: Dict[str, Any], lat: float, lon: float) -> Tuple[str, Optional[float], Optional[float], Optional[float], List[Dict[str, Any]]]:
    """
    Normalizes raw API provider output into standardized values:
    (status, congestion_level, current_speed_kmh, free_flow_speed_kmh, segments)
    """
    provider_name = _get_provider_name()

    current_speed = None
    free_flow_speed = None
    segments = []

    if provider_name == "tomtom" and "flowSegmentData" in raw:
        flow = raw["flowSegmentData"]
        current_speed = float(flow.get("currentSpeed", 0))
        free_flow_speed = float(flow.get("freeFlowSpeed", max(1.0, current_speed)))

        # Build segment coordinate if present
        coords = flow.get("coordinates", {}).get("coordinate", [])
        seg_lat = coords[0]["latitude"] if coords else lat
        seg_lon = coords[0]["longitude"] if coords else lon

        ratio = min(1.0, max(0.0, current_speed / free_flow_speed if free_flow_speed > 0 else 1.0))
        congestion = round(1.0 - ratio, 2)
        color = "#22c55e" if congestion < 0.33 else ("#f59e0b" if congestion < 0.66 else "#ef4444")

        segments.append({
            "segment_id": f"tomtom_seg_{round(lat,4)}_{round(lon,4)}",
            "latitude": seg_lat,
            "longitude": seg_lon,
            "current_speed_kmh": round(current_speed, 1),
            "free_flow_speed_kmh": round(free_flow_speed, 1),
            "traffic_ratio": round(ratio, 2),
            "congestion_level": congestion,
            "color": color,
        })
    else:
        # Fallback for generic provider response format
        current_speed = raw.get("current_speed_kmh")
        free_flow_speed = raw.get("free_flow_speed_kmh")
        if current_speed is not None and free_flow_speed is not None and free_flow_speed > 0:
            ratio = min(1.0, max(0.0, float(current_speed) / float(free_flow_speed)))
            congestion = round(1.0 - ratio, 2)
        else:
            congestion = raw.get("congestion_level")

    if congestion is None:
        status = "UNAVAILABLE"
    elif congestion < 0.33:
        status = "LOW"
    elif congestion < 0.66:
        status = "MEDIUM"
    else:
        status = "HIGH"

    return status, congestion, current_speed, free_flow_speed, segments


# ---------------------------------------------------------------------------
# Bounded Thread-Safe Cache with Freshness Tracking
# ---------------------------------------------------------------------------

class _TrafficCache:
    """
    Key: (round(lat, 3), round(lon, 3), int(radius_m))
    Value: (response_data_dict, fetched_at_timestamp)
    """
    def __init__(self, fresh_ttl: int = FRESH_TTL_SECONDS, stale_ttl: int = STALE_TTL_SECONDS, max_entries: int = MAX_CACHE_ENTRIES):
        self._lock = threading.RLock()
        self._fresh_ttl = fresh_ttl
        self._stale_ttl = stale_ttl
        self._max = max_entries
        self._store: Dict[Tuple, Tuple[Dict[str, Any], float]] = {}

    @staticmethod
    def _make_key(lat: float, lon: float, radius_m: float) -> Tuple:
        return (round(lat, 3), round(lon, 3), int(radius_m))

    def get(self, lat: float, lon: float, radius_m: float) -> Optional[Dict[str, Any]]:
        key = self._make_key(lat, lon, radius_m)
        now = time.time()

        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            data, fetched_at = entry
            age = now - fetched_at

            if age > self._stale_ttl:
                # Completely expired
                del self._store[key]
                return None

            result = dict(data)
            result["cached"] = True
            result["provider_status"] = "LIVE" if age <= self._fresh_ttl else "STALE"
            result["data_state"] = f"REAL/{result['provider_status']}"
            logger.info("[TrafficProvider] Data state: %s (cached=True, age=%.1fs)", result["data_state"], age)
            return result

    def set(self, lat: float, lon: float, radius_m: float, data: Dict[str, Any]) -> None:
        key = self._make_key(lat, lon, radius_m)
        with self._lock:
            if len(self._store) >= self._max:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            self._store[key] = (data, time.time())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = _TrafficCache()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_area_traffic(lat: float, lon: float, radius_m: float) -> Dict[str, Any]:
    """
    Fetches real traffic for the specified area coordinates and radius.

    Behavior:
      - Unconfigured env vars -> UNAVAILABLE / NOT_CONFIGURED
      - Cache hit (age <= 60s) -> REAL / LIVE
      - Cache hit (60s < age <= 300s) -> REAL / STALE
      - Provider error / exception -> UNAVAILABLE / ERROR
    """
    provider_name = _get_provider_name()
    api_key = _get_api_key()

    # 1. Check unconfigured state
    if not provider_name or not api_key:
        logger.debug("[TrafficProvider] No provider or API key configured.")
        return _unavailable_response("NOT_CONFIGURED")

    # 2. Check cache
    cached = _cache.get(lat, lon, radius_m)
    if cached is not None:
        return cached

    # 3. Request external provider
    raw, success = _fetch_from_provider(lat, lon, radius_m)
    if not success or raw is None:
        return _unavailable_response("ERROR")

    # 4. Normalize and store
    status, congestion, curr_spd, free_spd, segments = _normalize_provider_data(raw, lat, lon)
    now = time.time()
    response = _build_normalized_response(
        status=status,
        congestion_level=congestion,
        current_speed_kmh=curr_spd,
        free_flow_speed_kmh=free_spd,
        segments=segments,
        raw=raw,
        provider_status="LIVE",
        cached=False,
        fetched_at=now,
    )

    _cache.set(lat, lon, radius_m, response)
    return response


def clear_cache() -> None:
    _cache.clear()
