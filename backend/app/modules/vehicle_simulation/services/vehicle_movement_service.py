"""
VehicleMovementService — Sprint 4.3 / 6.5
Advances simulated vehicles along the existing NetworkX road graph.

Design rules:
- Movement is calculated from: distance = speed × elapsed_time (delta_seconds).
- Progress along an edge = distance_travelled / edge_length
- Multi-edge traversal: When edge_progress >= 1.0 the vehicle transitions to a 
  connected outgoing edge and continues moving with its remaining distance.
- Safety: Caps the maximum edge transitions per update to avoid infinite loops.
- If no outgoing edge exists (dead end) the vehicle stops at the current node.
- All DB writes are batched in a single commit and performed periodically.
"""
import logging
import random
import time
from datetime import datetime, timezone

from database.db import db
from ..models.vehicle import Vehicle
from .simulation_store import simulation_store
from ..constants import (
    MAX_VEHICLES_PER_TICK,
    DEFAULT_CACHE_KEY,
    VEHICLE_STATUS_ACTIVE,
    VEHICLE_STATUS_STOPPED,
    VEHICLE_STATUS_COMPLETED,
)
from ..utils.vehicle_utils import calculate_heading, interpolate_position
import app.modules.vehicle_simulation.services.route_store as route_store


import math


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class VehicleMovementService:
    """
    Stateless service that advances vehicle positions by a given delta_seconds
    using the existing in-memory NetworkX road graph.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.vehicle_simulation.movement")

    # ── Graph helpers ──────────────────────────────────────────────────────────

    def _get_nx_graph(self, cache_key: str):
        from app.modules.road_network.services.graph_service import graph_service
        nx_g = graph_service.get_nx_graph()
        if nx_g is None:
            graph_service.load_graph_from_cache(cache_key)
            nx_g = graph_service.get_nx_graph()
        return nx_g

    def _get_node_coords(self, nx_g, node_id: str):
        """Return (lat, lon) for a node, or None if not found / invalid."""
        if not node_id:
            return None
        # 1. Check active route_store nodes first (guarantees route geometry adherence)
        route_nodes = route_store.get_route_nodes()
        if route_nodes:
            str_nid = str(node_id)
            for n in route_nodes:
                if str(n.get("id")) == str_nid:
                    return float(n["lat"]), float(n["lon"])

        # 2. Fallback to nx_g node lookup
        if nx_g is not None and hasattr(nx_g, "nodes"):
            data = nx_g.nodes.get(node_id) or nx_g.nodes.get(int(node_id) if str(node_id).isdigit() else None, {})
            lat = data.get("lat", data.get("y"))
            lon = data.get("lon", data.get("x"))
            if lat is not None and lon is not None:
                try:
                    return float(lat), float(lon)
                except (TypeError, ValueError):
                    pass
        return None

    def _parse_edge_key(self, current_edge: str):
        """
        Parse edge string "src-dst-key" into (src, dst, key).
        Handles node IDs that may themselves contain hyphens by splitting from right.
        """
        try:
            parts = current_edge.rsplit("-", 1)
            key = int(parts[1]) if len(parts) == 2 else 0
            remainder = parts[0]
            mid = remainder.index("-")
            src = remainder[:mid]
            dst = remainder[mid + 1:]
            return src, dst, key
        except Exception:
            return None, None, 0

    def _get_edge_data_safe(self, nx_g, u, v, key=None):
        """Safely retrieve edge data trying string and int representations of node IDs."""
        if nx_g is None or u is None or v is None:
            return None
        data = nx_g.get_edge_data(u, v, key=key) if key is not None else nx_g.get_edge_data(u, v)
        if data:
            return data
        u_int = int(u) if str(u).isdigit() else u
        v_int = int(v) if str(v).isdigit() else v
        data = nx_g.get_edge_data(u_int, v_int, key=key) if key is not None else nx_g.get_edge_data(u_int, v_int)
        if data:
            return data
        data = nx_g.get_edge_data(str(u), str(v), key=key) if key is not None else nx_g.get_edge_data(str(u), str(v))
        return data

    def _get_edge_length(self, nx_g, src, dst, key=None) -> float:
        """Return edge length in km. Returns Haversine distance if edge data is missing."""
        try:
            data_map = self._get_edge_data_safe(nx_g, src, dst, key=key) or {}
            if isinstance(data_map, dict) and 0 in data_map:
                data_map = data_map[0]
            elif isinstance(data_map, dict) and len(data_map) > 0 and not ("length" in data_map or "distance" in data_map):
                data_map = next(iter(data_map.values()), {})
            length = float(data_map.get("length", data_map.get("distance", 0.0)) or 0.0)
            if length > 0:
                return length
        except Exception:
            pass

        # Fallback to Haversine distance between route node coordinates
        src_coords = self._get_node_coords(nx_g, str(src))
        dst_coords = self._get_node_coords(nx_g, str(dst))
        if src_coords and dst_coords:
            h_dist = _haversine_km(src_coords[0], src_coords[1], dst_coords[0], dst_coords[1])
            if h_dist > 0:
                return h_dist

        return 0.05

    def _is_route_destination(self, node_id: str) -> bool:
        """Return True if node_id is the final node of the active route."""
        route = route_store.get_route()
        if route is None:
            return False
        path_nodes = route.get("path_nodes") or []
        if not path_nodes:
            return False
        return str(node_id) == str(path_nodes[-1])

    def _get_route_next_node(self, current_node: str) -> str | None:
        """
        If there is an active stored route, return the next node in the
        route sequence after current_node. Returns None if:
        - No route is stored
        - current_node is not in the route
        - current_node is the final destination
        """
        route = route_store.get_route()
        if route is None:
            return None
        path_nodes = route.get("path_nodes") or []
        if not path_nodes:
            return None
        str_path = [str(n) for n in path_nodes]
        try:
            idx = str_path.index(str(current_node))
        except ValueError:
            return None
        if idx + 1 >= len(str_path):
            return None  # already at destination
        return str_path[idx + 1]

    def _pick_next_edge(self, nx_g, dst_node: str, rng: random.Random):
        """
        Pick the next edge to traverse from dst_node.

        Priority:
          1. Follow the stored route node sequence if dst_node is on it.
          2. If dst_node is the destination of the active route, return None.
          3. Randomly select a valid outgoing edge (fallback for non-route vehicles).

        Returns (new_src, new_dst, new_key, edge_data) or None if dead end / reached destination.
        """
        route = route_store.get_route()
        if route is not None:
            path_nodes = route.get("path_nodes") or []
            if path_nodes:
                str_path = [str(n) for n in path_nodes]
                str_dst = str(dst_node)
                if str_dst in str_path:
                    idx = str_path.index(str_dst)
                    if idx + 1 >= len(str_path):
                        # Reached final destination of active route
                        return None
                    route_next = str_path[idx + 1]
                    edge_data_map = self._get_edge_data_safe(nx_g, str_dst, route_next) or {}
                    key = 0
                    data = {}
                    if isinstance(edge_data_map, dict) and 0 in edge_data_map:
                        data = edge_data_map[0]
                    elif isinstance(edge_data_map, dict) and ("length" in edge_data_map or "distance" in edge_data_map):
                        data = edge_data_map
                    elif isinstance(edge_data_map, dict) and len(edge_data_map) > 0:
                        data = next(iter(edge_data_map.values()), {})
                    return str_dst, route_next, key, data

        # --- Fallback: random successor (only for non-route vehicles) ---
        successors = list(nx_g.successors(dst_node))
        if not successors and str(dst_node).isdigit():
            successors = list(nx_g.successors(int(dst_node)))
        if not successors:
            return None

        rng.shuffle(successors)
        for next_dst in successors:
            edge_data_map = self._get_edge_data_safe(nx_g, dst_node, next_dst)
            if not edge_data_map:
                continue
            key = 0
            if isinstance(edge_data_map, dict) and ("length" in edge_data_map or "distance" in edge_data_map):
                data = edge_data_map
            elif isinstance(edge_data_map, dict) and len(edge_data_map) > 0:
                data = edge_data_map.get(key, edge_data_map.get(list(edge_data_map.keys())[0], {}))
            else:
                data = {}

            if not isinstance(data, dict):
                data = {}
            length = float(data.get("length", data.get("distance", 0.0)) or 0.0)
            if length > 0:
                return str(dst_node), str(next_dst), key, data

        return None

    # ── Single-vehicle update ──────────────────────────────────────────────────

    def _advance_vehicle(self, vehicle: dict, nx_g, delta_seconds: float, rng: random.Random) -> bool:
        """
        Advance one vehicle (dict) by delta_seconds. Supports multi-edge traversal.

        Returns True if the vehicle was successfully updated, False otherwise.
        """
        if vehicle.get("status") != VEHICLE_STATUS_ACTIVE:
            return False
        if not vehicle.get("current_edge"):
            return False
        if vehicle.get("speed", 0) <= 0:
            return False

        src, dst, key = self._parse_edge_key(vehicle["current_edge"])
        if src is None:
            return False

        speed_kmh = max(vehicle["speed"], 0.0)
        remaining_dist_km = (speed_kmh / 3600.0) * delta_seconds

        if remaining_dist_km <= 0:
            return False

        max_transitions = 50
        transitions = 0
        has_moved = False

        while remaining_dist_km > 0 and transitions < max_transitions:
            edge_length_km = self._get_edge_length(nx_g, src, dst, key)
            if edge_length_km <= 0:
                edge_length_km = 0.1

            delta_prog = remaining_dist_km / edge_length_km
            current_prog = vehicle.get("edge_progress") or 0.0

            if current_prog + delta_prog < 1.0:
                # Vehicle finishes its movement on this edge
                new_progress = current_prog + delta_prog
                src_coords = self._get_node_coords(nx_g, str(src))
                dst_coords = self._get_node_coords(nx_g, str(dst))
                if src_coords and dst_coords:
                    lat, lon = interpolate_position(
                        src_coords[0], src_coords[1],
                        dst_coords[0], dst_coords[1],
                        new_progress,
                    )
                    vehicle["latitude"] = round(lat, 8)
                    vehicle["longitude"] = round(lon, 8)
                vehicle["edge_progress"] = round(new_progress, 6)
                remaining_dist_km = 0
                has_moved = True
            else:
                # Vehicle crosses the end of this edge
                prog_to_end = 1.0 - current_prog
                dist_to_end = prog_to_end * edge_length_km
                remaining_dist_km -= dist_to_end

                # Move to next edge
                vehicle["current_node"] = str(dst)
                next_edge = self._pick_next_edge(nx_g, str(dst), rng)

                if next_edge is None:
                    # Dead end or reached destination, stop here
                    dst_coords = self._get_node_coords(nx_g, str(dst))
                    if dst_coords:
                        vehicle["latitude"] = dst_coords[0]
                        vehicle["longitude"] = dst_coords[1]
                    vehicle["edge_progress"] = 1.0
                    if self._is_route_destination(str(dst)):
                        vehicle["status"] = VEHICLE_STATUS_COMPLETED
                    else:
                        vehicle["status"] = VEHICLE_STATUS_STOPPED
                    remaining_dist_km = 0
                    has_moved = True
                    break
                else:
                    new_src, new_dst, new_key, new_data = next_edge
                    src, dst, key = new_src, new_dst, new_key

                    vehicle["current_edge"] = f"{new_src}-{new_dst}-{new_key}"
                    vehicle["current_node"] = str(new_src)
                    vehicle["edge_progress"] = 0.0

                    n_src_coords = self._get_node_coords(nx_g, str(new_src))
                    n_dst_coords = self._get_node_coords(nx_g, str(new_dst))
                    if n_src_coords and n_dst_coords:
                        vehicle["heading"] = round(calculate_heading(
                            n_src_coords[0], n_src_coords[1],
                            n_dst_coords[0], n_dst_coords[1]
                        ), 2)
                        vehicle["latitude"] = n_src_coords[0]
                        vehicle["longitude"] = n_src_coords[1]

                    transitions += 1
                    has_moved = True

        if has_moved:
            vehicle["updated_at"] = datetime.now(timezone.utc).isoformat()

        return has_moved

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_vehicle_positions(
        self,
        delta_seconds: float,
        cache_key: str | None = None,
        seed: int | None = None,
    ) -> dict:
        """
        Advance all active vehicles by delta_seconds in memory.
        Persist to SQLite periodically to avoid locks.
        """
        logger = self._get_logger()

        if delta_seconds <= 0:
            raise ValueError("delta_seconds must be a positive number.")

        cache_key = cache_key or DEFAULT_CACHE_KEY
        nx_g = self._get_nx_graph(cache_key)
        if nx_g is None or nx_g.number_of_nodes() == 0:
            raise RuntimeError(
                "Road graph unavailable. Ingest via POST /api/road-network/ingest first."
            )

        rng = random.Random(seed)

        # 1. Fetch from in-memory store
        snapshot = simulation_store.get_snapshot()
        active_vehicles = [v for v in snapshot.get("vehicles", []) if v.get("status") == VEHICLE_STATUS_ACTIVE]

        tick_moved = 0
        tick_stopped = 0

        sim_id = simulation_store.simulation_id

        # 2. Update vehicles in memory
        for vehicle_dict in active_vehicles:
            prev_status = vehicle_dict.get("status")
            # Update the dictionary directly
            moved = self._advance_vehicle(vehicle_dict, nx_g, delta_seconds, rng)
            if moved:
                tick_moved += 1
                # Write back changes to simulation store
                simulation_store.update_vehicle(sim_id, vehicle_dict["vehicle_id"], vehicle_dict)
                
            if (vehicle_dict.get("status") in (VEHICLE_STATUS_STOPPED, VEHICLE_STATUS_COMPLETED)) and prev_status == VEHICLE_STATUS_ACTIVE:
                tick_stopped += 1

        # 3. Periodic SQLite Snapshot (e.g. every 5 seconds)
        current_time = time.time()
        time_since_snapshot = current_time - simulation_store.last_snapshot_time
        
        if time_since_snapshot >= 5.0 and sim_id:
            try:
                # Bulk update to database
                db_vehicles = db.session.execute(
                    db.select(Vehicle).where(Vehicle.simulation_id == sim_id)
                ).scalars().all()
                
                db_map = {v.vehicle_id: v for v in db_vehicles}
                memory_vehicles = simulation_store.get_snapshot()["vehicles"]
                
                for v_dict in memory_vehicles:
                    v_db = db_map.get(v_dict["vehicle_id"])
                    if v_db:
                        v_db.latitude = v_dict["latitude"]
                        v_db.longitude = v_dict["longitude"]
                        v_db.speed = v_dict["speed"]
                        v_db.heading = v_dict["heading"]
                        v_db.current_node = v_dict["current_node"]
                        v_db.current_edge = v_dict["current_edge"]
                        v_db.edge_progress = v_dict["edge_progress"]
                        v_db.status = v_dict["status"]
                        
                db.session.commit()
                simulation_store.set_last_snapshot_time(current_time)
                logger.debug("Committed batch snapshot to SQLite for %d vehicles.", len(memory_vehicles))
            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to commit batch snapshot: %s", exc)
                # Don't throw RuntimeError to avoid failing the real-time simulation tick!

        logger.info(
            "Simulation update: %.2fs — moved=%d, newly_stopped=%d",
            delta_seconds, tick_moved, tick_stopped
        )

        return {
            "vehicles_moved": tick_moved,
            "vehicles_stopped": tick_stopped,
            "delta_seconds": delta_seconds,
            "vehicles": simulation_store.get_snapshot()["vehicles"],
        }

    def get_snapshot(self) -> dict:
        """
        Return a lightweight snapshot of all vehicles' current state.
        Used by GET /api/vehicles/snapshot — efficient read for the frontend.
        """
        snapshot = simulation_store.get_snapshot()
        return {
            "count": snapshot["count"],
            "vehicles": snapshot["vehicles"],
        }


vehicle_movement_service = VehicleMovementService()
