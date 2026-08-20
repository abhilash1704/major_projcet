"""
Traffic Cost Service — Sprint 9A

Calculates traffic-aware edge costs and penalties by mapping active simulated vehicles
and hotspot severities onto road network graph edges.

Maintains base distance / travel time intact and computes separate traffic_aware_cost.
"""
import logging
import math
import time
from datetime import datetime, timezone
from flask import current_app

from .traffic_data_service import traffic_data_service
from .hotspot_service import hotspot_service


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Utility to calculate great-circle distance in meters between two lat/lon points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TrafficCostService:
    """
    Centralized service for road segment traffic costs and penalty calculations.
    """

    def __init__(self):
        self._cached_result = None
        self._last_calc_time = 0.0
        self._version = 0
        self._ttl_seconds = 3.0

    def _get_logger(self):
        return logging.getLogger("routeflow.traffic_intelligence.cost")

    def _get_config(self, key: str, default: float | int):
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            return default

    def get_traffic_state_version(self) -> int:
        return self._version

    def invalidate_cache(self):
        self._cached_result = None
        self._version += 1

    def get_cached_costs(self) -> dict:
        now = time.time()
        if self._cached_result is not None and (now - self._last_calc_time < self._ttl_seconds):
            return self._cached_result
        return self.calculate_traffic_costs()

    def calculate_traffic_costs(self) -> dict:
        """
        Calculates edge-level traffic penalties and traffic-aware costs.
        
        Returns:
            dict containing total_active_vehicles, total_affected_edges,
            breakdown (low, medium, high), processing_time_ms, and edge_costs list.
        """
        now = time.time()
        logger = self._get_logger()
        t0 = time.perf_counter()

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Fetch vehicle snapshot and hotspots
        try:
            snapshot = traffic_data_service.get_active_vehicle_snapshot()
            vehicles = snapshot.get("vehicles", [])
        except Exception as exc:
            logger.warning("Vehicle snapshot unavailable for traffic cost calculation: %s", exc)
            vehicles = []

        try:
            hotspot_response = hotspot_service.detect_hotspots()
            hotspots = hotspot_response.get("hotspots", [])
        except Exception as exc:
            logger.warning("Hotspot detection failed during traffic cost calculation: %s", exc)
            hotspots = []

        if not vehicles:
            t1 = time.perf_counter()
            return {
                "success": True,
                "timestamp": timestamp,
                "total_active_vehicles": 0,
                "total_affected_edges": 0,
                "low_traffic_edges": 0,
                "medium_traffic_edges": 0,
                "high_traffic_edges": 0,
                "processing_time_ms": round((t1 - t0) * 1000, 2),
                "edge_costs": []
            }

        # 2. Retrieve graph instance (O(1) reference)
        from app.modules.road_network.services.graph_service import graph_service
        nx_g = graph_service.get_nx_graph()

        if nx_g is None or len(nx_g) == 0:
            logger.warning("Road graph not loaded — returning default empty traffic costs")
            t1 = time.perf_counter()
            return {
                "success": True,
                "timestamp": timestamp,
                "total_active_vehicles": len(vehicles),
                "total_affected_edges": 0,
                "low_traffic_edges": 0,
                "medium_traffic_edges": 0,
                "high_traffic_edges": 0,
                "processing_time_ms": round((t1 - t0) * 1000, 2),
                "edge_costs": []
            }

        # 3. Map vehicles to edges O(N)
        # Vehicles store current_edge = "u-v-k"
        edge_vehicle_map: dict[str, list[dict]] = {}
        for v in vehicles:
            e_key = v.get("current_edge")
            if not e_key:
                continue
            if e_key not in edge_vehicle_map:
                edge_vehicle_map[e_key] = []
            edge_vehicle_map[e_key].append(v)

        # Configurable penalty multipliers
        penalty_low = self._get_config('TRAFFIC_PENALTY_FACTOR_LOW', 1.15)
        penalty_medium = self._get_config('TRAFFIC_PENALTY_FACTOR_MEDIUM', 1.60)
        penalty_high = self._get_config('TRAFFIC_PENALTY_FACTOR_HIGH', 3.00)

        severity_rank = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        penalty_factors = {
            "NONE": 1.0,
            "LOW": penalty_low,
            "MEDIUM": penalty_medium,
            "HIGH": penalty_high
        }

        node_data_dict = dict(nx_g.nodes(data=True))
        affected_edges = []
        low_count = 0
        med_count = 0
        high_count = 0

        # Build candidate edges from edges with vehicles + edges inside hotspot radii
        candidate_edge_keys = set(edge_vehicle_map.keys())

        # Match hotspots to edges within radius
        for hs in hotspots:
            h_lat = hs["center_latitude"]
            h_lon = hs["center_longitude"]
            h_rad = hs["radius_meters"]
            h_sev = hs["severity"]

            # Evaluate candidate edges whose midpoint is within hotspot circle
            # Check edge vehicle map keys and graph edges
            for e_key in list(edge_vehicle_map.keys()):
                parts = e_key.split('-')
                if len(parts) >= 2:
                    u_id, v_id = parts[0], parts[1]
                    u_node = node_data_dict.get(u_id, node_data_dict.get(int(u_id) if u_id.isdigit() else u_id, {}))
                    v_node = node_data_dict.get(v_id, node_data_dict.get(int(v_id) if v_id.isdigit() else v_id, {}))

                    u_lat = u_node.get("lat", u_node.get("y"))
                    u_lon = u_node.get("lon", u_node.get("x"))
                    v_lat = v_node.get("lat", v_node.get("y"))
                    v_lon = v_node.get("lon", v_node.get("x"))

                    if u_lat is not None and v_lat is not None:
                        mid_lat = (float(u_lat) + float(v_lat)) / 2.0
                        mid_lon = (float(u_lon) + float(v_lon)) / 2.0
                        dist_m = _haversine_meters(h_lat, h_lon, mid_lat, mid_lon)
                        if dist_m <= h_rad:
                            candidate_edge_keys.add(e_key)

        for e_key in candidate_edge_keys:
            v_list = edge_vehicle_map.get(e_key, [])
            veh_count = len(v_list)

            parts = e_key.split('-')
            if len(parts) < 2:
                continue

            u_id, v_id = parts[0], parts[1]
            key_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 0

            # Retrieve edge weight data from graph
            raw_edge_data = nx_g.get_edge_data(u_id, v_id)
            if raw_edge_data is None:
                # Try integer node IDs if string lookup failed
                u_int = int(u_id) if u_id.isdigit() else u_id
                v_int = int(v_id) if v_id.isdigit() else v_id
                raw_edge_data = nx_g.get_edge_data(u_int, v_int)

            if not raw_edge_data:
                continue

            if isinstance(raw_edge_data, dict) and key_id in raw_edge_data:
                e_attrs = raw_edge_data[key_id]
            elif isinstance(raw_edge_data, dict):
                e_attrs = next(iter(raw_edge_data.values()), {})
            else:
                e_attrs = {}

            base_distance_km = e_attrs.get("length", e_attrs.get("distance", 0.1))
            if base_distance_km > 50:  # If in meters, convert to km
                base_distance_km = base_distance_km / 1000.0

            base_travel_time_sec = e_attrs.get("travel_time", base_distance_km * 60.0)

            # Determine traffic level
            # 1. Hotspot circle proximity check
            highest_sev = "NONE"
            u_node = node_data_dict.get(u_id, node_data_dict.get(int(u_id) if u_id.isdigit() else u_id, {}))
            v_node = node_data_dict.get(v_id, node_data_dict.get(int(v_id) if v_id.isdigit() else v_id, {}))
            u_lat = u_node.get("lat", u_node.get("y"))
            u_lon = u_node.get("lon", u_node.get("x"))
            v_lat = v_node.get("lat", v_node.get("y"))
            v_lon = v_node.get("lon", v_node.get("x"))

            if u_lat is not None and v_lat is not None:
                mid_lat = (float(u_lat) + float(v_lat)) / 2.0
                mid_lon = (float(u_lon) + float(v_lon)) / 2.0
                for hs in hotspots:
                    dist_m = _haversine_meters(hs["center_latitude"], hs["center_longitude"], mid_lat, mid_lon)
                    if dist_m <= hs["radius_meters"]:
                        if severity_rank[hs["severity"]] > severity_rank[highest_sev]:
                            highest_sev = hs["severity"]

            # 2. Vehicle count density check
            if veh_count >= 15 or highest_sev == "HIGH":
                edge_severity = "HIGH"
                high_count += 1
            elif veh_count >= 5 or highest_sev == "MEDIUM":
                edge_severity = "MEDIUM"
                med_count += 1
            elif veh_count >= 1 or highest_sev == "LOW":
                edge_severity = "LOW"
                low_count += 1
            else:
                continue

            mult = penalty_factors[edge_severity]
            traffic_penalty = round(base_travel_time_sec * (mult - 1.0), 2)
            traffic_aware_cost = round(base_travel_time_sec * mult, 2)

            affected_edges.append({
                "edge_id": e_key,
                "source_node": u_id,
                "target_node": v_id,
                "vehicle_count": veh_count,
                "base_distance_km": round(base_distance_km, 4),
                "base_travel_time_sec": round(base_travel_time_sec, 2),
                "traffic_level": edge_severity,
                "penalty_factor": mult,
                "traffic_penalty": traffic_penalty,
                "traffic_aware_cost": traffic_aware_cost,
            })

        t1 = time.perf_counter()
        processing_ms = round((t1 - t0) * 1000, 2)

        logger.info(
            "Traffic Cost Calculation: Vehicles=%d | Affected Edges=%d (L:%d M:%d H:%d) | Time=%.2fms",
            len(vehicles), len(affected_edges), low_count, med_count, high_count, processing_ms
        )

        res = {
            "success": True,
            "timestamp": timestamp,
            "version": self._version + 1,
            "total_active_vehicles": len(vehicles),
            "total_affected_edges": len(affected_edges),
            "low_traffic_edges": low_count,
            "medium_traffic_edges": med_count,
            "high_traffic_edges": high_count,
            "processing_time_ms": processing_ms,
            "edge_costs": affected_edges
        }
        self._version += 1
        self._cached_result = res
        self._last_calc_time = now
        return res


traffic_cost_service = TrafficCostService()
