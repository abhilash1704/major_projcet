"""
VehicleGenerator — Sprint 4.2 / 5.5

Generates simulated vehicles placed along the currently calculated A* road route.

Key design rules:
- When route_nodes are provided (list of {"id", "lat", "lon"}), vehicles are
  distributed evenly across the complete route using cumulative-distance positioning.
- Falls back to graph-wide random edge placement only when no route is active.
- Uses existing graph_service singleton — does NOT duplicate graph logic.
- Calculates headings from sequential route geometry.
- Uses road speed_limit for realistic initial speeds.
- Supports configurable random seed for reproducible tests.
- Delegates persistence to VehicleService.bulk_create_vehicles().

Route-based distribution algorithm:
  1. Build cumulative distance array over route node pairs.
  2. For N vehicles, target positions at:  (i + 0.5) / N * total_distance  (equal-spaced, midpoints)
  3. Add small jitter bounded to ±(segment_length / N / 2) so vehicles stay on-route.
  4. Interpolate (lat, lon) and track current_node / edge_progress for movement engine.
"""
import math
import random
import logging
from collections import defaultdict

from ..constants import (
    DEFAULT_GENERATION_COUNT,
    MAX_GENERATION_COUNT,
    SPEED_FRACTION,
    FALLBACK_SPEED_KMH,
    SPEED_NOISE_FRACTION,
    MAX_VEHICLES_PER_EDGE,
    DEFAULT_RANDOM_SEED,
    DEFAULT_CACHE_KEY,
    VEHICLE_STATUS_ACTIVE,
)
from ..utils.vehicle_utils import calculate_heading, interpolate_position
from ..models.vehicle import _generate_vehicle_id
from .vehicle_service import vehicle_service
from .route_store import get_route_nodes


# ── Haversine helper (local, no circular imports) ────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class VehicleGenerator:
    """
    Generates simulated vehicles on the active road route or (fallback) on
    valid road segments of the NetworkX graph.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.vehicle_simulation.generator")

    # ── Graph access ─────────────────────────────────────────────────────────

    def _get_nx_graph(self, cache_key: str):
        """Load the NetworkX graph from the existing graph_service singleton."""
        from app.modules.road_network.services.graph_service import graph_service
        nx_g = graph_service.get_nx_graph()
        if nx_g is None:
            graph_service.load_graph_from_cache(cache_key)
            nx_g = graph_service.get_nx_graph()
        return nx_g

    # ── Edge validation (fallback path) ─────────────────────────────────────

    def _collect_valid_edges(self, nx_g) -> list[tuple]:
        """Return (u, v, key, data, slat, slon, dlat, dlon) for all usable edges."""
        valid = []
        node_data = dict(nx_g.nodes(data=True))
        for u, v, k, data in nx_g.edges(data=True, keys=True):
            src = node_data.get(u, {})
            dst = node_data.get(v, {})
            src_lat = src.get("lat", src.get("y"))
            src_lon = src.get("lon", src.get("x"))
            dst_lat = dst.get("lat", dst.get("y"))
            dst_lon = dst.get("lon", dst.get("x"))
            if None in (src_lat, src_lon, dst_lat, dst_lon):
                continue
            try:
                slat, slon = float(src_lat), float(src_lon)
                dlat, dlon = float(dst_lat), float(dst_lon)
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(slat) and math.isfinite(slon)
                    and math.isfinite(dlat) and math.isfinite(dlon)):
                continue
            length = data.get("length", data.get("distance", 0.0)) or 0.0
            if length <= 0:
                continue
            valid.append((u, v, k, data, slat, slon, dlat, dlon))
        return valid

    # ── Speed calculation ─────────────────────────────────────────────────────

    def _calculate_speed(self, edge_data: dict | None, rng: random.Random) -> float:
        """Calculate a realistic vehicle speed using edge speed_limit."""
        speed_limit = (edge_data or {}).get("speed_limit")
        if speed_limit and float(speed_limit) > 0:
            base = float(speed_limit) * SPEED_FRACTION
        else:
            base = FALLBACK_SPEED_KMH
        noise = rng.uniform(-SPEED_NOISE_FRACTION, SPEED_NOISE_FRACTION)
        return max(0.0, round(base * (1.0 + noise), 2))

    # ── Route-based distribution ──────────────────────────────────────────────

    def _build_cumulative_distances(self, route_nodes: list[dict]) -> list[float]:
        """
        Build a cumulative distance array for the route.
        cum_dist[i] = total distance from node 0 to node i  (km).
        """
        cum = [0.0]
        for i in range(1, len(route_nodes)):
            n0 = route_nodes[i - 1]
            n1 = route_nodes[i]
            d = _haversine_km(n0["lat"], n0["lon"], n1["lat"], n1["lon"])
            cum.append(cum[-1] + d)
        return cum

    def _locate_on_route(
        self,
        target_dist_km: float,
        route_nodes: list[dict],
        cum_dist: list[float],
    ) -> tuple:
        """
        Given a target cumulative distance, find the route segment and interpolate.

        Returns:
            (lat, lon, from_node_id, to_node_id, edge_progress)
        """
        total = cum_dist[-1]
        # Clamp to valid range
        target_dist_km = max(0.0, min(total, target_dist_km))

        # Binary-search for the segment
        lo, hi = 0, len(cum_dist) - 2
        seg = hi  # default to last segment
        for i in range(len(cum_dist) - 1):
            if cum_dist[i] <= target_dist_km <= cum_dist[i + 1]:
                seg = i
                break

        n0 = route_nodes[seg]
        n1 = route_nodes[seg + 1]
        seg_len = cum_dist[seg + 1] - cum_dist[seg]

        if seg_len > 0:
            progress = (target_dist_km - cum_dist[seg]) / seg_len
        else:
            progress = 0.0
        progress = max(0.0, min(1.0, progress))

        lat, lon = interpolate_position(n0["lat"], n0["lon"], n1["lat"], n1["lon"], progress)
        return lat, lon, str(n0["id"]), str(n1["id"]), progress

    def _generate_route_vehicles(
        self,
        count: int,
        route_nodes: list[dict],
        nx_g,
        rng: random.Random,
    ) -> list[dict]:
        """
        Distribute `count` vehicles evenly along `route_nodes` with small jitter.
        """
        logger = self._get_logger()

        if len(route_nodes) < 2:
            raise RuntimeError(
                "Route has fewer than 2 nodes — cannot distribute vehicles."
            )

        cum_dist = self._build_cumulative_distances(route_nodes)
        total_km = cum_dist[-1]

        if total_km <= 0.0:
            raise RuntimeError("Route total distance is zero — cannot distribute vehicles.")

        logger.info(
            "Route-based generation: %d vehicles on %.3f km route (%d nodes).",
            count, total_km, len(route_nodes),
        )

        # Equal spacing with midpoint offset: vehicles at 0.5/N, 1.5/N, 2.5/N … (N-0.5)/N
        # Keep a small margin from both endpoints (5% of route length on each side)
        MARGIN = 0.05
        start_km = total_km * MARGIN
        end_km = total_km * (1.0 - MARGIN)
        span_km = end_km - start_km

        if span_km <= 0:
            start_km = 0.0
            end_km = total_km
            span_km = total_km

        ideal_spacing_km = span_km / max(count, 1)

        # Step 6: Minimum Vehicle Spacing
        MIN_VEHICLE_SPACING_METERS = 25
        min_spacing_km = MIN_VEHICLE_SPACING_METERS / 1000.0

        # Gracefully reduce effective spacing if vehicle count is extremely high
        effective_min_spacing = min(min_spacing_km, ideal_spacing_km * 0.8)

        # Step 4: Controlled Randomness
        DISTRIBUTION_JITTER = 0.4  # Allow up to 40% jitter within the spacing slot
        safe_jitter_km = max(0.0, (ideal_spacing_km - effective_min_spacing) / 2.0)
        max_jitter_preference = ideal_spacing_km * DISTRIBUTION_JITTER
        jitter_max_km = min(max_jitter_preference, safe_jitter_km)

        # Generate target positions
        positions_km = []
        for i in range(count):
            ideal_km = start_km + (i + 0.5) * ideal_spacing_km
            jitter = rng.uniform(-jitter_max_km, jitter_max_km)
            target_km = max(start_km, min(end_km, ideal_km + jitter))
            positions_km.append(target_km)

        # Step 7: Guarantee minimum spacing to avoid artificial clusters
        for i in range(1, len(positions_km)):
            if positions_km[i] - positions_km[i-1] < effective_min_spacing:
                positions_km[i] = min(positions_km[i-1] + effective_min_spacing, total_km)

        vehicle_data_list: list[dict] = []

        for target_km in positions_km:

            lat, lon, from_node, to_node, edge_prog = self._locate_on_route(
                target_km, route_nodes, cum_dist
            )

            # Heading from current segment direction
            seg_idx = 0
            for j in range(len(cum_dist) - 1):
                if cum_dist[j] <= target_km <= cum_dist[j + 1]:
                    seg_idx = j
                    break
            n0 = route_nodes[seg_idx]
            n1 = route_nodes[min(seg_idx + 1, len(route_nodes) - 1)]
            heading = calculate_heading(n0["lat"], n0["lon"], n1["lat"], n1["lon"])

            # Speed from graph edge (if available) or fallback
            edge_data = None
            if nx_g is not None:
                raw_edge = nx_g.get_edge_data(from_node, to_node)
                if raw_edge:
                    if isinstance(raw_edge, dict) and 0 in raw_edge:
                        edge_data = raw_edge[0]
                    elif isinstance(raw_edge, dict):
                        edge_data = next(iter(raw_edge.values()), None)

            speed = self._calculate_speed(edge_data, rng)
            current_edge = f"{from_node}-{to_node}-0"

            vehicle_data_list.append({
                "vehicle_id":    _generate_vehicle_id(),
                "latitude":      round(lat, 8),
                "longitude":     round(lon, 8),
                "speed":         speed,
                "heading":       round(heading, 2),
                "current_node":  from_node,
                "current_edge":  current_edge,
                "edge_progress": round(edge_prog, 6),
                "status":        VEHICLE_STATUS_ACTIVE,
            })

        return vehicle_data_list

    # ── Fallback: random-edge generation (legacy, no active route) ────────────

    def _build_vehicle_data(
        self, u, v, k, edge_data,
        src_lat, src_lon, dst_lat, dst_lon,
        rng: random.Random,
    ) -> dict:
        fraction = rng.uniform(0.1, 0.9)
        lat, lon = interpolate_position(src_lat, src_lon, dst_lat, dst_lon, fraction)
        heading = calculate_heading(src_lat, src_lon, dst_lat, dst_lon)
        speed = self._calculate_speed(edge_data, rng)
        current_edge = f"{u}-{v}-{k}"
        return {
            "vehicle_id":    _generate_vehicle_id(),
            "latitude":      round(lat, 8),
            "longitude":     round(lon, 8),
            "speed":         speed,
            "heading":       round(heading, 2),
            "current_node":  str(u),
            "current_edge":  current_edge,
            "edge_progress": round(fraction, 6),
            "status":        VEHICLE_STATUS_ACTIVE,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        count: int | None = None,
        seed: int | None = None,
        cache_key: str | None = None,
        route_nodes: list[dict] | None = None,
        simulation_id: str | None = None,
    ) -> dict:
        """
        Generate ``count`` vehicles.

        If route_nodes is provided (or module-level _active_route_nodes is set),
        vehicles are distributed evenly along the route.

        Otherwise falls back to random edge placement across the whole graph.

        Args:
            count:       Number of vehicles to generate (1 – MAX_GENERATION_COUNT).
            seed:        Optional random seed for reproducibility.
            cache_key:   Road graph cache key (default = bangalore_default).
            route_nodes: Optional list of {"id", "lat", "lon"} dicts from route result.
            simulation_id: The active simulation session ID to assign to these vehicles.

        Returns:
            dict with keys: generated (int), failed (int), vehicles (list), mode (str).
        """
        logger = self._get_logger()

        count = int(count) if count is not None else DEFAULT_GENERATION_COUNT
        if count <= 0:
            raise ValueError("count must be a positive integer.")
        if count > MAX_GENERATION_COUNT:
            raise ValueError(
                f"count {count} exceeds maximum allowed ({MAX_GENERATION_COUNT})."
            )

        cache_key = cache_key or DEFAULT_CACHE_KEY
        rng = random.Random(seed if seed is not None else DEFAULT_RANDOM_SEED)

        nx_g = self._get_nx_graph(cache_key)
        if nx_g is None or nx_g.number_of_nodes() == 0:
            raise RuntimeError(
                "Road graph is unavailable. "
                "Please ingest the road network via POST /api/road-network/ingest first."
            )

        # Prefer explicitly passed route_nodes, then route_store singleton
        effective_route = route_nodes or get_route_nodes()

        # ── Route-based generation ────────────────────────────────────────────
        if effective_route and len(effective_route) >= 2:
            vehicle_data_list = self._generate_route_vehicles(count, effective_route, nx_g, rng)
            mode = "route"
        else:
            # ── Fallback: random edges across the whole graph ─────────────────
            logger.warning(
                "No active route — falling back to random edge placement. "
                "Call POST /api/routes/calculate first for route-based generation."
            )
            valid_edges = self._collect_valid_edges(nx_g)
            if not valid_edges:
                raise RuntimeError("No valid road edges found in the graph.")

            edge_population: dict[str, int] = defaultdict(int)
            vehicle_data_list = []
            attempts = 0
            max_attempts = count * 10

            while len(vehicle_data_list) < count and attempts < max_attempts:
                attempts += 1
                edge_tuple = rng.choice(valid_edges)
                u, v, k, data, slat, slon, dlat, dlon = edge_tuple
                edge_key = f"{u}-{v}-{k}"
                if edge_population[edge_key] >= MAX_VEHICLES_PER_EDGE:
                    if len(valid_edges) > 1:
                        continue
                edge_population[edge_key] += 1
                vdata = self._build_vehicle_data(u, v, k, data, slat, slon, dlat, dlon, rng)
                vehicle_data_list.append(vdata)

            if not vehicle_data_list:
                raise RuntimeError("Could not build any vehicle data from the road graph.")
            mode = "graph"

        # Assign simulation_id
        if simulation_id:
            for vdata in vehicle_data_list:
                vdata["simulation_id"] = simulation_id

        # ── Persist via vehicle_service ───────────────────────────────────────
        created_vehicles, failed_count = vehicle_service.bulk_create_vehicles(vehicle_data_list)

        from ..schemas.vehicle_schema import VehicleSchema
        result_data = VehicleSchema.dump_many(created_vehicles)

        logger.info(
            "Generation complete [mode=%s]: %d created, %d failed.",
            mode, len(created_vehicles), failed_count,
        )

        return {
            "generated": len(created_vehicles),
            "failed":    failed_count,
            "vehicles":  result_data,
            "mode":      mode,
        }


vehicle_generator = VehicleGenerator()
