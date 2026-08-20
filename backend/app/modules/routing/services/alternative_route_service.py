"""
alternative_route_service.py — RouteFlow High-Traffic Alternative Route Engine

Generates 2–3 algorithmically diverse alternative routes using both A* and Dijkstra
when HIGH traffic is detected on the active route.

Key requirements:
1. Reuses existing A* and Dijkstra routing implementations from routing_service.py.
2. Reuses existing traffic costs from traffic_cost_service.py.
3. Filters duplicate and highly similar routes (similarity threshold check).
4. Ranks candidates based on traffic-aware total cost.
5. Ensures thread safety so only one calculation runs for a given route event.
6. Operates strictly within the 30-second target processing limit.
7. Leaves existing simulation and database state untouched.
"""

import logging
import time
import threading
import concurrent.futures
from flask import current_app

from app.services.routing_service import routing_service
from app.modules.road_network.services.graph_service import graph_service

logger = logging.getLogger("routeflow.routing.alternative")

COLOR_PALETTE = ["#22c55e", "#3b82f6"]  # Green (Alt 1 — BEST), Blue (Alt 2)
LABEL_PALETTE = ["Alternative 1 — BEST", "Alternative 2"]

# Active calculation safety lock dictionary: {calc_key: Lock}
_calculation_locks = {}
_locks_guard = threading.Lock()

# Cache for recent calculation results to prevent redundant calculations during repeated HIGH requests
_result_cache = {}
_cache_guard = threading.Lock()
_CACHE_TTL_SECONDS = 15.0


def _compute_route_similarity(path1_nodes, path2_nodes):
    """
    Computes Jaccard/overlap similarity ratio between two node paths.
    Returns float in [0.0, 1.0] where 1.0 means identical node sets.
    """
    if not path1_nodes or not path2_nodes:
        return 0.0
    set1 = set(str(n) for n in path1_nodes)
    set2 = set(str(n) for n in path2_nodes)
    intersection_size = len(set1.intersection(set2))
    min_size = min(len(set1), len(set2))
    if min_size == 0:
        return 0.0
    return intersection_size / min_size


class AlternativeRouteService:
    """
    Independent engine for calculating diverse alternative routes during high traffic.
    """

    def generate_alternative_routes(
        self,
        source_node,
        destination_node,
        current_route=None,
        traffic_level="HIGH",
        max_alternatives=2,
        request_id=None
    ):
        """
        Generates up to 2 genuinely different alternative routes using A* and Dijkstra.

        :param source_node: Raw ID or canonical ID of start node
        :param destination_node: Raw ID or canonical ID of destination node
        :param current_route: Dict containing current active route details (path_nodes, distance, etc.)
        :param traffic_level: Current traffic level string (e.g. "HIGH")
        :param max_alternatives: Maximum number of alternative routes to return (default 2)
        :param request_id: Unique request identifier for stale protection tracking
        :return: Standardized result dict with current_route and alternatives list
        """
        t0 = time.time()

        src_str = str(source_node).strip() if source_node else ""
        tgt_str = str(destination_node).strip() if destination_node else ""

        if not src_str or not tgt_str or src_str == tgt_str:
            return {
                "success": False,
                "status": "error",
                "trigger": "INVALID_PARAMS",
                "reason": "invalid_parameters",
                "message": "Valid source and destination nodes are required",
                "current_route": current_route or {},
                "alternatives": []
            }

        # Calculation key for thread & request safety lock
        calc_key = f"{src_str}_{tgt_str}_{traffic_level}"

        # Check cached result if recent
        with _cache_guard:
            cached = _result_cache.get(calc_key)
            if cached:
                cached_time, cached_res = cached
                if time.time() - cached_time < _CACHE_TTL_SECONDS:
                    logger.info("[ALT_ENGINE] Returning cached alternative routes for key %s", calc_key)
                    res_copy = dict(cached_res)
                    if request_id:
                        res_copy["request_id"] = request_id
                    return res_copy

        # Obtain per-key lock to prevent parallel duplicate calculations
        with _locks_guard:
            if calc_key not in _calculation_locks:
                _calculation_locks[calc_key] = threading.Lock()
            calc_lock = _calculation_locks[calc_key]

        with calc_lock:
            # Re-check cache after lock acquisition
            with _cache_guard:
                cached = _result_cache.get(calc_key)
                if cached:
                    cached_time, cached_res = cached
                    if time.time() - cached_time < _CACHE_TTL_SECONDS:
                        res_copy = dict(cached_res)
                        if request_id:
                            res_copy["request_id"] = request_id
                        return res_copy

            return self._execute_candidate_generation(
                src_str=src_str,
                tgt_str=tgt_str,
                current_route=current_route,
                traffic_level=traffic_level,
                max_alternatives=min(int(max_alternatives), 2),
                request_id=request_id,
                calc_key=calc_key,
                t0=t0
            )

    def _execute_candidate_generation(
        self,
        src_str,
        tgt_str,
        current_route,
        traffic_level,
        max_alternatives,
        request_id,
        calc_key,
        t0
    ):
        logger.info("[ALT_ENGINE] Starting alternative route calculation for %s -> %s [Trigger: %s]",
                    src_str, tgt_str, traffic_level)

        # 1. Gather live traffic cost snapshot (consistent snapshot for both A* and Dijkstra)
        traffic_costs_map = {}
        try:
            from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service
            tc_data = traffic_cost_service.get_cached_costs()
            if tc_data and tc_data.get("success"):
                for ec in tc_data.get("edge_costs", []):
                    e_key = ec.get("edge_id")
                    if e_key:
                        traffic_costs_map[e_key] = ec
                    u_s, v_s = str(ec.get("source_node")), str(ec.get("target_node"))
                    traffic_costs_map[(u_s, v_s)] = ec
                    traffic_costs_map[f"{u_s}-{v_s}-0"] = ec
        except Exception as exc:
            logger.warning("[ALT_ENGINE] Could not fetch live traffic costs: %s", exc)

        # 2. Extract current route nodes / geometry
        current_nodes = []
        if current_route:
            if "path_nodes" in current_route:
                current_nodes = [str(n) for n in current_route["path_nodes"]]
            elif "nodes" in current_route and isinstance(current_route["nodes"], list):
                current_nodes = [str(n.get("id", n)) if isinstance(n, dict) else str(n) for n in current_route["nodes"]]

        # If current route nodes not provided, calculate baseline route first
        if not current_nodes:
            try:
                base_res = routing_service.calculate_route(
                    source_node=src_str,
                    destination_node=tgt_str,
                    algorithm="astar",
                    routing_mode="traffic_aware"
                )
                if base_res and base_res.get("success"):
                    current_nodes = [str(n["id"]) for n in base_res.get("nodes", [])]
                    if not current_route:
                        current_route = base_res
            except Exception as exc:
                logger.warning("[ALT_ENGINE] Failed to calculate baseline route: %s", exc)

        # Build congestion penalty map over current route edges
        congested_penalties = {}
        penalty_base = 5.0
        if len(current_nodes) >= 2:
            for i in range(len(current_nodes) - 1):
                u = current_nodes[i]
                v = current_nodes[i + 1]
                e_key_0 = f"{u}-{v}-0"
                c_info = traffic_costs_map.get(e_key_0) or traffic_costs_map.get((u, v))
                lvl = c_info.get("traffic_level") if c_info else "HIGH"
                mult = penalty_base if lvl == "HIGH" else penalty_base * 0.6
                congested_penalties[e_key_0] = mult
                congested_penalties[(u, v)] = mult

        # 3. Configure Candidate Search Specs (Dual Algorithm: A* + Dijkstra)
        # Config 1 & 2 run pure traffic-aware search; remaining configs apply temporary edge penalties to diversify
        candidate_configs = [
            {"algo": "astar", "penalty_mult": 1.0},
            {"algo": "dijkstra", "penalty_mult": 1.0},
            {"algo": "astar", "penalty_mult": 2.5},
            {"algo": "dijkstra", "penalty_mult": 2.5},
            {"algo": "astar", "penalty_mult": 4.5},
            {"algo": "dijkstra", "penalty_mult": 4.5},
        ]

        raw_candidates = []
        HARD_TIMEOUT_SECONDS = 28.0  # Safe timeout inside 30.0s hard limit

        def _worker(cfg):
            if (time.time() - t0) >= HARD_TIMEOUT_SECONDS:
                return cfg["algo"], None
            penalties = {}
            if cfg["penalty_mult"] > 1.0:
                for k, val in congested_penalties.items():
                    penalties[k] = val * cfg["penalty_mult"]
            try:
                res = routing_service.calculate_route(
                    source_node=src_str,
                    destination_node=tgt_str,
                    algorithm=cfg["algo"],
                    routing_mode="traffic_aware",
                    reroute_penalties=penalties if penalties else None
                )
                return cfg["algo"], res
            except Exception as e:
                logger.warning("[ALT_ENGINE] Worker error (%s, mult=%.1f): %s", cfg["algo"], cfg["penalty_mult"], e)
                return cfg["algo"], None


        # Check timeout before executing
        if (time.time() - t0) >= 30.0:
            return {
                "success": False,
                "status": "error",
                "reason": "timeout",
                "message": "Alternative route calculation timed out.",
                "current_route": current_route or {},
                "alternatives": []
            }

        # Execute parallel searches
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(candidate_configs))
        try:
            futures = [executor.submit(_worker, cfg) for cfg in candidate_configs]
            for future in concurrent.futures.as_completed(futures, timeout=HARD_TIMEOUT_SECONDS):
                try:
                    algo_used, alt_res = future.result()
                    if alt_res and alt_res.get("success"):
                        raw_candidates.append((algo_used, alt_res))
                except Exception as fe:
                    logger.warning("[ALT_ENGINE] Future resolution error: %s", fe)
            executor.shutdown(wait=False)
        except concurrent.futures.TimeoutError:
            logger.warning("[ALT_ENGINE] Search timed out at %.1fs", HARD_TIMEOUT_SECONDS)
            executor.shutdown(wait=False, cancel_futures=True)
            if not raw_candidates:
                return {
                    "success": False,
                    "status": "error",
                    "reason": "timeout",
                    "message": "Alternative route calculation timed out.",
                    "current_route": current_route or {},
                    "alternatives": []
                }
        except Exception as exc:
            executor.shutdown(wait=False)
            logger.error("[ALT_ENGINE] Parallel search error: %s", exc)


        # 4. Diversity Filtering & Ranking
        # Requirement: 80% shared edge similarity threshold (sim >= 0.80 treated as duplicate)
        SIMILARITY_THRESHOLD = 0.80

        candidate_routes = []
        seen_paths = [current_nodes] if current_nodes else []

        for algo_used, alt in raw_candidates:
            if len(candidate_routes) >= max_alternatives:
                break

            alt_nodes = [str(n["id"]) for n in alt.get("nodes", [])]
            if len(alt_nodes) < 2:
                continue

            # Check similarity against current route and existing accepted candidate paths
            too_similar = False
            for existing_p in seen_paths:
                sim = _compute_route_similarity(alt_nodes, existing_p)
                if sim >= SIMILARITY_THRESHOLD:
                    too_similar = True
                    break

            if too_similar:
                logger.info("[ALT_ENGINE] Candidate rejected due to similarity >= %.0f%%", SIMILARITY_THRESHOLD * 100)
                continue

            seen_paths.append(alt_nodes)

            # Compute traffic cost & metrics
            dist_km = round(alt.get("distance_km", 0.0), 2)
            time_sec = alt.get("travel_time_seconds", 0.0)
            eta_min = round(time_sec / 60.0, 1)
            t_cost = round(alt.get("traffic_cost", 0.0), 1)
            total_cost = round(alt.get("total_cost", time_sec + t_cost), 1)
            traffic_lvl = alt.get("traffic_level", "LOW")

            alt_obj = {
                "id": f"alternative_{len(candidate_routes) + 1}",
                "rank": len(candidate_routes) + 1,
                "algorithm": "A*" if algo_used == "astar" else "Dijkstra",
                "distance_km": dist_km,
                "total_distance_km": dist_km,
                "eta_minutes": eta_min,
                "eta_seconds": time_sec,
                "travel_time_seconds": time_sec,
                "total_duration_seconds": time_sec,
                "traffic_level": traffic_lvl,
                "traffic_cost": t_cost,
                "total_cost": total_cost,
                "score": total_cost,
                "path": alt_nodes,
                "nodes": alt.get("nodes", []),
                "geometry": alt.get("geometry", []),
                "congested_segments": alt.get("congested_segments", [])
            }
            candidate_routes.append(alt_obj)

        # 5. Rank alternatives by traffic-adjusted total_cost (lowest first)
        candidate_routes.sort(key=lambda x: x["total_cost"])

        # Assign rank, colors and labels
        for idx, alt_item in enumerate(candidate_routes):
            alt_item["id"] = f"alternative_{idx + 1}"
            alt_item["rank"] = idx + 1
            alt_item["color"] = COLOR_PALETTE[min(idx, len(COLOR_PALETTE) - 1)]
            alt_item["label"] = LABEL_PALETTE[min(idx, len(LABEL_PALETTE) - 1)]

        elapsed_ms = round((time.time() - t0) * 1000, 1)

        # Check final timeout
        if (time.time() - t0) >= 30.0:
            return {
                "success": False,
                "status": "error",
                "reason": "timeout",
                "message": "Alternative route calculation timed out.",
                "current_route": current_route or {},
                "alternatives": []
            }

        # Format response
        curr_dist = current_route.get("distance_km") or current_route.get("total_distance_km") if current_route else 0.0
        curr_eta = current_route.get("eta_minutes") or round((current_route.get("travel_time_seconds") or 0.0) / 60.0, 1) if current_route else 0.0

        current_route_info = {
            "distance_km": curr_dist,
            "eta_seconds": (current_route.get("travel_time_seconds") if current_route else 0.0) or (curr_eta * 60),
            "eta_minutes": curr_eta,
            "traffic_level": traffic_level,
            "traffic_cost": current_route.get("traffic_cost", 0.0) if current_route else 0.0
        }

        status_str = "success" if len(candidate_routes) > 0 else "partial"
        message_str = f"Found {len(candidate_routes)} alternative route(s)." if len(candidate_routes) > 0 else "No suitable alternative route found."

        result = {
            "success": True,
            "status": status_str,
            "trigger": "HIGH_TRAFFIC",
            "message": message_str,
            "request_id": request_id,
            "generation_time_ms": elapsed_ms,
            "execution_time_ms": elapsed_ms,
            "current_route": current_route_info,
            "alternatives": candidate_routes
        }

        # Cache result
        with _cache_guard:
            _result_cache[calc_key] = (time.time(), result)

        logger.info("[ALT_ENGINE] Calculation completed in %.1f ms | Found %d alternative route(s)",
                    elapsed_ms, len(candidate_routes))
        return result


# Singleton instance
alternative_route_service = AlternativeRouteService()
