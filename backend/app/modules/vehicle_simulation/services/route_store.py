"""
route_store.py — Sprint 5.5

Module-level singleton that stores the most recently calculated route so that:
  1. vehicle_generator can place vehicles along it.
  2. vehicle_movement_service can advance vehicles along the same node sequence.

This avoids sending the full route geometry on every request and keeps the
architecture consistent with the existing graph_service singleton pattern.
"""
from __future__ import annotations
from typing import Any

# ── In-memory route state ────────────────────────────────────────────────────

_route_data: dict[str, Any] | None = None
_algorithm: str = "astar"
_routing_mode: str = "normal"
_last_reroute_time: float = 0.0
_last_evaluation_time: float = 0.0
_reroute_reason: str = ""
_reroute_status: str = "stable"
_original_cost: float = 0.0
_current_cost: float = 0.0
_previous_route: dict[str, Any] | None = None
_previous_route_cost: float = 0.0

def set_route(route: dict[str, Any] | None, algorithm: str = "astar", routing_mode: str = "normal") -> None:
    """
    Persist route data returned by routing_service.calculate_route().
    """
    global _route_data, _algorithm, _routing_mode, _last_reroute_time, _reroute_reason, _reroute_status, _original_cost, _current_cost, _previous_route, _previous_route_cost
    
    if route is not None:
        if _route_data is not None and _route_data.get("geometry") != route.get("geometry"):
            _previous_route = _route_data
            _previous_route_cost = _current_cost
            import time
            _last_reroute_time = time.time()
            
        _route_data = route
        _algorithm = algorithm
        _routing_mode = routing_mode
        _original_cost = float(route.get("total_cost", route.get("travel_time_seconds", 0.0)))
        _current_cost = _original_cost
        if _reroute_status != "rerouting_evaluation":
            _reroute_reason = ""
            _reroute_status = "stable"
    else:
        _route_data = None
        _previous_route = None
        _previous_route_cost = 0.0
        _last_reroute_time = 0.0
        _reroute_reason = ""
        _reroute_status = "stable"


def get_route() -> dict[str, Any] | None:
    """Return the currently stored route dict, or None."""
    return _route_data

def get_algorithm() -> str:
    return _algorithm

def get_routing_mode() -> str:
    return _routing_mode

def set_routing_mode(m: str) -> None:
    global _routing_mode
    _routing_mode = m

def get_last_reroute_time() -> float:
    return _last_reroute_time

def set_last_reroute_time(t: float) -> None:
    global _last_reroute_time
    _last_reroute_time = t

def get_reroute_reason() -> str:
    return _reroute_reason

def set_reroute_reason(r: str) -> None:
    global _reroute_reason
    _reroute_reason = r

def get_reroute_status() -> str:
    return _reroute_status

def set_reroute_status(s: str) -> None:
    global _reroute_status
    _reroute_status = s

def get_original_cost() -> float:
    return _original_cost

def set_original_cost(c: float) -> None:
    global _original_cost
    _original_cost = c

def get_current_cost() -> float:
    return _current_cost

def set_current_cost(c: float) -> None:
    global _current_cost
    _current_cost = c

def get_route_nodes() -> list[dict] | None:
    """
    Return route nodes as [{"id": str, "lat": float, "lon": float}, ...],
    or None if no route is stored.
    """
    if _route_data is None:
        return None
    geometry = _route_data.get("geometry") or []
    path_nodes = _route_data.get("path_nodes") or []
    if len(geometry) < 2 or len(path_nodes) < 2:
        return None
    # Pair node IDs with coordinates
    result = []
    for i, (lat_lon) in enumerate(geometry):
        node_id = path_nodes[i] if i < len(path_nodes) else f"node_{i}"
        result.append({
            "id":  str(node_id),
            "lat": float(lat_lon[0]),
            "lon": float(lat_lon[1]),
        })
    return result


def get_last_evaluation_time() -> float:
    return _last_evaluation_time

def set_last_evaluation_time(t: float) -> None:
    global _last_evaluation_time
    _last_evaluation_time = t

def get_previous_route() -> dict[str, Any] | None:
    return _previous_route

def get_previous_route_cost() -> float:
    return _previous_route_cost

def set_previous_route_cost(c: float) -> None:
    global _previous_route_cost
    _previous_route_cost = c


def clear_route() -> None:
    """Clear the stored route (e.g. on simulation reset or new route calc)."""
    global _route_data
    _route_data = None
    set_route(None)
