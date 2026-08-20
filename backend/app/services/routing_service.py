"""
routing_service.py — RouteFlow Core Routing Engine

Performance characteristics:
  - Graph fetched from singleton in-memory instance (0 ms graph load per request)
  - No Overpass API calls, no OSM ingestion, no graph rebuild during routing
  - In-memory LRU route-result cache for repeated identical requests (< 1 ms)
  - Detailed [ROUTE PERF] timing logs for profiling
  - 40-second hard timeout guard per request
  - Geographic bounding-box subgraph for very long routes (with full-graph fallback)
"""

import logging
import math
import time
import threading
from functools import lru_cache
from collections import OrderedDict

import networkx as nx
from flask import current_app

from app.modules.road_network.services.graph_service import graph_service
from app.modules.road_network.services.node_service import node_service
from app.modules.road_network.utils.geo_utils import haversine_distance
import app.modules.vehicle_simulation.services.route_store as route_store

class GraphProxy:
    """Wrapper to count unique nodes explored during A*/Dijkstra pathfinding."""
    def __init__(self, g):
        self._g = g
        self.explored = set()

    def __getattr__(self, name):
        attr = getattr(self._g, name)
        if name in ('adj', '_adj', 'succ', '_succ'):
            class AdjProxy:
                def __init__(self, adj, explored):
                    self._adj = adj
                    self._explored = explored
                def __getitem__(self, node):
                    self._explored.add(node)
                    return self._adj[node]
                def __contains__(self, node):
                    return node in self._adj
                def __len__(self):
                    return len(self._adj)
                def __iter__(self):
                    return iter(self._adj)
            return AdjProxy(attr, self.explored)
        return attr

    def __getitem__(self, node):
        self.explored.add(node)
        return self._g[node]

    def __len__(self):
        return len(self._g)

    def __contains__(self, node):
        return node in self._g

    def __iter__(self):
        return iter(self._g)



SUPPORTED_ALGORITHMS = {"astar", "dijkstra"}

# Route result in-memory cache  ─────────────────────────────────────────────
_ROUTE_CACHE_MAX = 128
_route_cache: OrderedDict = OrderedDict()
_route_cache_lock = threading.Lock()

# Hard timeout (seconds) per route calculation request
ROUTE_TIMEOUT_SECONDS = 40


def _cache_put(key, value):
    with _route_cache_lock:
        if key in _route_cache:
            _route_cache.move_to_end(key)
        _route_cache[key] = value
        if len(_route_cache) > _ROUTE_CACHE_MAX:
            _route_cache.popitem(last=False)


def _cache_get(key):
    with _route_cache_lock:
        if key in _route_cache:
            _route_cache.move_to_end(key)
            return _route_cache[key]
    return None


def _haversine_heuristic(u, v, nx_graph):
    """
    A* geographic heuristic: haversine distance between node u and node v.
    Uses precomputed node attributes — no on-the-fly lookups.
    """
    try:
        u_data = nx_graph.nodes[u]
        v_data = nx_graph.nodes[v]
        u_lat = u_data.get('lat', u_data.get('y'))
        u_lon = u_data.get('lon', u_data.get('x'))
        v_lat = v_data.get('lat', v_data.get('y'))
        v_lon = v_data.get('lon', v_data.get('x'))
        if u_lat is not None and u_lon is not None and v_lat is not None and v_lon is not None:
            return haversine_distance(float(u_lat), float(u_lon), float(v_lat), float(v_lon))
    except Exception:
        pass
    return 0.0


def normalize_node_id(raw_id, nx_graph):
    """
    Resolves raw node ID (str or int) against graph.
    Returns canonical graph key or None.
    """
    if raw_id is None:
        return None
    as_str = str(raw_id).strip()
    if as_str in nx_graph:
        return as_str
    try:
        as_int = int(as_str)
        if as_int in nx_graph:
            return as_int
    except (ValueError, TypeError):
        pass
    return None


def _build_subgraph_for_corridor(nx_g, src_node, tgt_node, margin_factor=0.5):
    """
    Builds a geographic corridor subgraph around the src→dst bounding box.
    Corridor margin = max(0.2°, straight-line span * margin_factor).

    Returns the subgraph, or the full graph if nodes have no coordinates.
    This avoids exploring 517k nodes when routing within a small city area.
    """
    src_data = nx_g.nodes.get(src_node, {})
    tgt_data = nx_g.nodes.get(tgt_node, {})

    src_lat = src_data.get('lat', src_data.get('y'))
    src_lon = src_data.get('lon', src_data.get('x'))
    tgt_lat = tgt_data.get('lat', tgt_data.get('y'))
    tgt_lon = tgt_data.get('lon', tgt_data.get('x'))

    if src_lat is None or tgt_lat is None:
        return nx_g, False  # Can't build corridor — use full graph

    lat_span = abs(float(tgt_lat) - float(src_lat))
    lon_span = abs(float(tgt_lon) - float(src_lon))
    margin = max(0.25, max(lat_span, lon_span) * margin_factor)

    min_lat = min(float(src_lat), float(tgt_lat)) - margin
    max_lat = max(float(src_lat), float(tgt_lat)) + margin
    min_lon = min(float(src_lon), float(tgt_lon)) - margin
    max_lon = max(float(src_lon), float(tgt_lon)) + margin

    candidate_nodes = [
        n for n, d in nx_g.nodes(data=True)
        if (
            min_lat <= float(d.get('lat', d.get('y', min_lat - 1))) <= max_lat and
            min_lon <= float(d.get('lon', d.get('x', min_lon - 1))) <= max_lon
        )
    ]

    # Only use subgraph if it meaningfully reduces node count AND contains both endpoints
    if len(candidate_nodes) < len(nx_g) * 0.9 and src_node in candidate_nodes and tgt_node in candidate_nodes:
        return nx_g.subgraph(candidate_nodes), True

    return nx_g, False


class RoutingService:
    """
    Core Routing Engine for RouteFlow.

    Supports A* and Dijkstra pathfinding over the cached NetworkX graph.
    Implements an in-memory route-result LRU cache.
    Enforces a 40-second hard timeout per request.
    """

    def clear_route_cache(self):
        with _route_cache_lock:
            _route_cache.clear()

    def _get_logger(self):
        try:
            if current_app and hasattr(current_app, 'logger') and current_app.logger:
                return current_app.logger
        except Exception:
            pass
        return logging.getLogger("routeflow.routing_engine")

    def calculate_route(
        self,
        source_node,
        destination_node,
        algorithm="astar",
        source_lat=None,
        source_lon=None,
        destination_lat=None,
        destination_lon=None,
        weight="travel_time",
        routing_mode="normal",
        reroute_penalties=None
    ):
        """
        Calculate optimal path between source_node and destination_node.

        Performance guarantees:
          - Graph load time: 0 ms (reuses preloaded singleton)
          - Nearest-node lookup: not performed here (node IDs already resolved)
          - Route cache check: < 1 ms
          - Hard timeout: 40 seconds

        :param source_node: Raw ID of starting road graph node
        :param destination_node: Raw ID of destination road graph node
        :param algorithm: 'astar' (default) or 'dijkstra'
        :param source_lat/lon, destination_lat/lon: Optional coords for re-resolution
        :param weight: 'travel_time' or 'length'
        :param routing_mode: 'normal' (default) or 'traffic_aware'
        :raises ValueError: Invalid parameters, unsupported algorithm, no path
        :raises RuntimeError: Graph unavailable
        """
        logger = self._get_logger()
        t_total_start = time.perf_counter()

        # ── Input validation ──────────────────────────────────────────────────
        if not source_node or not destination_node:
            raise ValueError("source_node and destination_node are required")

        algo_name = (algorithm or "astar").strip().lower()
        if algo_name not in SUPPORTED_ALGORITHMS:
            raise ValueError("Unsupported routing algorithm")

        mode_name = (routing_mode or "normal").strip().lower()
        if mode_name not in {"normal", "traffic_aware"}:
            mode_name = "normal"

        src_raw_str = str(source_node).strip()
        tgt_raw_str = str(destination_node).strip()

        if src_raw_str == tgt_raw_str:
            raise ValueError("source_node and destination_node must be different")

        weight_attr = 'travel_time' if weight == 'travel_time' else 'length'

        # ── Fetch Traffic Costs snapshot (if traffic_aware mode) ─────────────
        traffic_costs_map = {}
        traffic_version = 0
        if mode_name == "traffic_aware":
            try:
                from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service
                costs_data = traffic_cost_service.get_cached_costs()
                traffic_version = costs_data.get("version", 0)
                for ec in costs_data.get("edge_costs", []):
                    traffic_costs_map[ec["edge_id"]] = ec
                    u_str, v_str = str(ec["source_node"]), str(ec["target_node"])
                    traffic_costs_map[f"{u_str}-{v_str}-0"] = ec
                    traffic_costs_map[(u_str, v_str)] = ec
            except Exception as exc:
                logger.warning("Traffic cost service query failed; falling back to normal costs: %s", exc)

        # ── Get in-memory graph (0 ms — preloaded at startup) ─────────────────
        t_graph_start = time.perf_counter()
        nx_g = graph_service.get_nx_graph_safe()
        t_graph_ms = (time.perf_counter() - t_graph_start) * 1000

        # ── Route cache check (< 1 ms for repeated requests on same graph) ───
        cache_key = (src_raw_str, tgt_raw_str, algo_name, mode_name, traffic_version, nx_g.number_of_nodes())
        
        if reroute_penalties:
            cached = None
        else:
            cached = _cache_get(cache_key)

        if cached is not None:
            logger.info("[ROUTE PERF] Cache HIT: %s → %s via %s [%s] (0 ms)",
                        src_raw_str, tgt_raw_str, algo_name, mode_name)
            try:
                if route_store.get_reroute_status() != "rerouting_evaluation":
                    route_store.set_route({
                        "path_nodes": [n["id"] for n in cached["nodes"]],
                        "geometry": cached["geometry"],
                        "source_node_id": cached["source_node"],
                        "target_node_id": cached["destination_node"],
                        "total_distance_km": cached["distance_km"],
                        "total_duration_seconds": cached["travel_time_seconds"],
                        "total_cost": cached.get("total_cost", cached["travel_time_seconds"])
                    }, algorithm=algo_name, routing_mode=mode_name)
            except Exception as e:
                logger.warning("Failed to restore route in route_store: %s", e)
            return cached

        logger.info("[ROUTE PERF] Graph fetch: %.1f ms (%d nodes, %d edges) | Mode: %s (v%d)",
                    t_graph_ms, nx_g.number_of_nodes(), nx_g.number_of_edges(), mode_name, traffic_version)

        # ── Node ID normalisation ──────────────────────────────────────────────
        src = normalize_node_id(src_raw_str, nx_g)
        tgt = normalize_node_id(tgt_raw_str, nx_g)

        # Fallback re-resolution if node ID not in current graph but coords available
        if src is None and source_lat is not None and source_lon is not None:
            try:
                resolved = node_service.find_nearest_node(float(source_lat), float(source_lon))
                if resolved and resolved.get("success", False):
                    src = normalize_node_id(resolved["node_id"], nx_g)
                    logger.info("Source node %s not in graph; re-resolved to: %s", src_raw_str, src)
            except Exception as exc:
                logger.warning("Source re-resolution failed: %s", exc)

        if tgt is None and destination_lat is not None and destination_lon is not None:
            try:
                resolved = node_service.find_nearest_node(float(destination_lat), float(destination_lon))
                if resolved and resolved.get("success", False):
                    tgt = normalize_node_id(resolved["node_id"], nx_g)
                    logger.info("Destination node %s not in graph; re-resolved to: %s", tgt_raw_str, tgt)
            except Exception as exc:
                logger.warning("Destination re-resolution failed: %s", exc)

        if src is None:
            raise ValueError(
                f"Source node '{src_raw_str}' is not present in the routing graph "
                f"({nx_g.number_of_nodes()} nodes loaded)."
            )
        if tgt is None:
            raise ValueError(
                f"Destination node '{tgt_raw_str}' is not present in the routing graph "
                f"({nx_g.number_of_nodes()} nodes loaded)."
            )

        src = str(src)
        tgt = str(tgt)

        # ── Geographic corridor subgraph (optional optimisation) ───────────────
        t_sub_start = time.perf_counter()
        routing_graph, used_subgraph = _build_subgraph_for_corridor(nx_g, src, tgt)
        t_sub_ms = (time.perf_counter() - t_sub_start) * 1000
        if used_subgraph:
            logger.info("[ROUTE PERF] Corridor subgraph: %d nodes (%.0f ms)",
                        routing_graph.number_of_nodes(), t_sub_ms)

        # ── Define Edge Weight Function ─────────────────────────────────────────
        def custom_weight_fn(u, v, data):
            if isinstance(data, dict) and len(data) > 0 and isinstance(next(iter(data.values())), dict):
                best_cost = float('inf')
                for k, attrs in data.items():
                    base_w = float(attrs.get('travel_time', attrs.get('length', 0.1)) or 0.1) if weight_attr == 'travel_time' else float(attrs.get('length', attrs.get('distance', 0.1)) or 0.1)
                    if weight_attr == 'length' and base_w > 50:
                        base_w /= 1000.0
                    
                    if mode_name == "traffic_aware":
                        e_key1 = f"{u}-{v}-{k}"
                        e_key2 = f"{u}-{v}-0"
                        cost_info = traffic_costs_map.get(e_key1) or traffic_costs_map.get(e_key2) or traffic_costs_map.get((str(u), str(v)))
                        if cost_info:
                            penalty_mult = cost_info.get("penalty_factor", 1.0)
                            c = base_w * penalty_mult
                        else:
                            c = base_w
                        
                        if reroute_penalties:
                            extra = reroute_penalties.get(e_key1) or reroute_penalties.get(e_key2) or reroute_penalties.get((str(u), str(v)), 1.0)
                            c *= extra
                    else:
                        c = base_w

                    if c < best_cost:
                        best_cost = c
                return max(0.0, best_cost)
            else:
                attrs = data if isinstance(data, dict) else {}
                base_w = float(attrs.get('travel_time', attrs.get('length', 0.1)) or 0.1) if weight_attr == 'travel_time' else float(attrs.get('length', attrs.get('distance', 0.1)) or 0.1)
                if weight_attr == 'length' and base_w > 50:
                    base_w /= 1000.0

                if mode_name == "traffic_aware":
                    e_key1 = f"{u}-{v}-0"
                    cost_info = traffic_costs_map.get(e_key1) or traffic_costs_map.get((str(u), str(v)))
                    penalty_mult = 1.0
                    if cost_info:
                        penalty_mult = cost_info.get("penalty_factor", 1.0)
                    
                    c = base_w * penalty_mult
                    if reroute_penalties:
                        extra = reroute_penalties.get(e_key1) or reroute_penalties.get((str(u), str(v)), 1.0)
                        c *= extra

                    return max(0.0, c)
                return max(0.0, base_w)

        weight_to_pass = custom_weight_fn if mode_name == "traffic_aware" else weight_attr

        # ── Pathfinding with 40-second timeout ────────────────────────────────
        t_path_start = time.perf_counter()
        path_nodes = None
        result_holder = {}

        def _run_pathfinding():
            try:
                gp = GraphProxy(routing_graph)
                if algo_name == 'dijkstra':
                    result_holder['path'] = nx.dijkstra_path(gp, src, tgt, weight=weight_to_pass)
                else:
                    heuristic_fn = lambda u, v: _haversine_heuristic(u, v, routing_graph)
                    result_holder['path'] = nx.astar_path(
                        gp, src, tgt,
                        heuristic=heuristic_fn,
                        weight=weight_to_pass
                    )
                result_holder['nodes_explored'] = len(gp.explored)
            except nx.NetworkXNoPath:
                result_holder['error'] = 'NO_PATH'
                result_holder['message'] = f"No valid road path exists between '{src}' and '{tgt}'."
            except nx.NodeNotFound as exc:
                result_holder['error'] = 'NODE_NOT_FOUND'
                result_holder['message'] = str(exc)
            except Exception as exc:
                result_holder['error'] = 'ROUTING_ERROR'
                result_holder['message'] = f"Route calculation failed: {str(exc)}"

        thread = threading.Thread(target=_run_pathfinding, daemon=True)
        thread.start()
        thread.join(timeout=ROUTE_TIMEOUT_SECONDS)

        t_path_ms = (time.perf_counter() - t_path_start) * 1000

        if thread.is_alive():
            logger.error("[ROUTE PERF] TIMEOUT: %s [%s] %s exceeded %ds (%.0f ms elapsed)",
                         algo_name, mode_name, src + "→" + tgt, ROUTE_TIMEOUT_SECONDS, t_path_ms)
            raise TimeoutError(
                f"Route calculation exceeded the {ROUTE_TIMEOUT_SECONDS} second limit. "
                "Try a closer source and destination."
            )

        if 'error' in result_holder:
            err = result_holder['error']
            msg = result_holder['message']
            logger.warning("[ROUTE PERF] %s (%s, %s): %s", err, algo_name, mode_name, msg)
            if err == 'NO_PATH':
                if used_subgraph:
                    logger.info("[ROUTE PERF] Retrying on full graph after corridor found no path")
                    result_holder.clear()

                    def _run_full():
                        try:
                            gp_full = GraphProxy(nx_g)
                            if algo_name == 'dijkstra':
                                result_holder['path'] = nx.dijkstra_path(gp_full, src, tgt, weight=weight_to_pass)
                            else:
                                heuristic_fn = lambda u, v: _haversine_heuristic(u, v, nx_g)
                                result_holder['path'] = nx.astar_path(
                                    gp_full, src, tgt,
                                    heuristic=heuristic_fn,
                                    weight=weight_to_pass
                                )
                            result_holder['nodes_explored'] = len(gp_full.explored)
                        except nx.NetworkXNoPath:
                            result_holder['error'] = 'NO_PATH'
                            result_holder['message'] = f"No valid road path exists between '{src}' and '{tgt}'."
                        except Exception as exc:
                            result_holder['error'] = 'ROUTING_ERROR'
                            result_holder['message'] = str(exc)

                    elapsed_so_far = time.perf_counter() - t_total_start
                    remaining = ROUTE_TIMEOUT_SECONDS - elapsed_so_far
                    if remaining > 2:
                        t2 = threading.Thread(target=_run_full, daemon=True)
                        t2.start()
                        t2.join(timeout=remaining)
                        if t2.is_alive():
                            raise TimeoutError(
                                f"Route calculation exceeded the {ROUTE_TIMEOUT_SECONDS} second limit."
                            )
                        if 'error' in result_holder:
                            raise ValueError(result_holder['message'])
                    else:
                        raise TimeoutError(
                            f"Route calculation exceeded the {ROUTE_TIMEOUT_SECONDS} second limit."
                        )
                else:
                    raise ValueError(msg)
            else:
                raise ValueError(msg)

        path_nodes = result_holder.get('path')
        if not path_nodes:
            raise ValueError(f"No valid road path exists between '{src}' and '{tgt}'.")

        logger.info("[ROUTE PERF] Pathfinding (%s, %s): %.0f ms, %d nodes",
                    algo_name, mode_name, t_path_ms, len(path_nodes))

        # ── Geometry extraction & Traffic Metric Calculation ─────────────────
        t_recon_start = time.perf_counter()
        geometry = []
        nodes_out = []
        edges_out = []
        total_dist_km = 0.0
        total_time_sec = 0.0
        total_base_cost = 0.0
        total_traffic_penalty = 0.0
        max_severity_rank = 0
        severity_map = {0: "NONE", 1: "LOW", 2: "MEDIUM", 3: "HIGH"}
        rank_lookup = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

        for i, node_id in enumerate(path_nodes):
            node_data = nx_g.nodes.get(node_id, {})
            lat = node_data.get('lat', node_data.get('y', 0.0))
            lon = node_data.get('lon', node_data.get('x', 0.0))

            if lat is not None and lon is not None:
                lat_f, lon_f = float(lat), float(lon)
                geometry.append([lat_f, lon_f])
                nodes_out.append({"id": str(node_id), "lat": lat_f, "lon": lon_f})
            else:
                nodes_out.append({"id": str(node_id), "lat": 0.0, "lon": 0.0})

            if i < len(path_nodes) - 1:
                next_id = path_nodes[i + 1]
                edge_data_map = nx_g.get_edge_data(node_id, next_id) or {}

                best_key, best_edge, best_tt = 0, {}, float("inf")
                if isinstance(edge_data_map, dict):
                    for k, ed in edge_data_map.items():
                        tt = float(ed.get('travel_time', ed.get('length', 0.0)) or 0.0)
                        if tt < best_tt:
                            best_tt, best_key, best_edge = tt, k, ed

                length_raw = float(best_edge.get('length', best_edge.get('distance', 0.0)) or 0.0)
                if length_raw > 50:
                    length_raw /= 1000.0
                time_sec = float(best_edge.get('travel_time', 0.0) or (length_raw * 60.0))

                total_dist_km += length_raw
                total_time_sec += time_sec
                total_base_cost += time_sec

                e_key1 = f"{node_id}-{next_id}-{best_key}"
                e_key2 = f"{node_id}-{next_id}-0"
                cost_info = traffic_costs_map.get(e_key1) or traffic_costs_map.get(e_key2) or traffic_costs_map.get((str(node_id), str(next_id)))

                if cost_info:
                    p_factor = cost_info.get("penalty_factor", 1.0)
                    t_penalty = time_sec * (p_factor - 1.0)
                    t_level = cost_info.get("traffic_level", "NONE")
                else:
                    t_penalty = 0.0
                    t_level = "NONE"

                total_traffic_penalty += t_penalty
                sev_r = rank_lookup.get(t_level, 0)
                if sev_r > max_severity_rank:
                    max_severity_rank = sev_r

                edges_out.append({
                    "source": str(node_id),
                    "target": str(next_id),
                    "key": best_key,
                    "length": round(length_raw, 6),
                    "travel_time": round(time_sec, 4),
                    "speed_limit": float(best_edge.get("speed_limit", 0.0) or 0.0),
                    "highway": str(best_edge.get("highway", "road")),
                    "oneway": bool(best_edge.get("oneway", False)),
                })

        total_dist_km = round(total_dist_km, 3)
        total_time_sec = round(total_time_sec, 1)
        eta_minutes = round(total_time_sec / 60.0, 1)
        base_cost_val = round(total_base_cost, 1)
        traffic_cost_val = round(total_traffic_penalty, 1)
        total_cost_val = round(total_base_cost + total_traffic_penalty, 1)
        traffic_level_val = severity_map[max_severity_rank]
        t_recon_ms = (time.perf_counter() - t_recon_start) * 1000

        # ── Build result ───────────────────────────────────────────────────────
        result = {
            "status": "success",
            "success": True,
            "algorithm": algo_name,
            "routing_mode": mode_name,
            "source_node": src,
            "destination_node": tgt,
            "nodes": nodes_out,
            "edges": edges_out,
            "distance_km": total_dist_km,
            "total_distance_km": total_dist_km,
            "travel_time_seconds": total_time_sec,
            "total_travel_time_seconds": total_time_sec,
            "eta_minutes": eta_minutes,
            "base_cost": base_cost_val,
            "traffic_cost": traffic_cost_val,
            "total_cost": total_cost_val,
            "route_cost": total_cost_val,
            "traffic_level": traffic_level_val,
            "geometry": geometry,
            "execution_time_ms": round(t_path_ms, 2),
            "nodes_explored": result_holder.get('nodes_explored', 0),
            "route_nodes": len(path_nodes),
        }

        # ── Store in route_store for vehicle simulation ─────────────────────────
        if route_store.get_reroute_status() != "rerouting_evaluation":
            route_store.set_route({
                "path_nodes": path_nodes,
                "geometry": geometry,
                "source_node_id": src,
                "target_node_id": tgt,
                "total_distance_km": total_dist_km,
                "total_duration_seconds": total_time_sec,
                "total_cost": total_cost_val
            }, algorithm=algo_name, routing_mode=mode_name)

        # ── Cache result ───────────────────────────────────────────────────────
        if not reroute_penalties:
            _cache_put(cache_key, result)

        # ── Performance summary log ────────────────────────────────────────────
        t_total_ms = (time.perf_counter() - t_total_start) * 1000
        logger.info(
            "[ROUTE PERF] TOTAL: %.0f ms | Graph: %.0f ms | Path: %.0f ms | Recon: %.0f ms | "
            "%s → %s via %s [%s] | %.2f km | %.1f s (~%.1f min) | %d nodes | Traffic level: %s",
            t_total_ms, t_graph_ms, t_path_ms, t_recon_ms,
            src, tgt, algo_name, mode_name, total_dist_km, total_time_sec, eta_minutes, len(path_nodes), traffic_level_val
        )

        return result

    def _calculate_path_metrics(self, nx_g, path_nodes, traffic_costs_map, routing_mode="traffic_aware"):
        """Helper to calculate cost, ETA, distance and construct geometry for a sequence of nodes."""
        geometry = []
        nodes_out = []
        edges_out = []
        total_dist_km = 0.0
        total_time_sec = 0.0
        total_base_cost = 0.0
        total_traffic_penalty = 0.0
        max_severity_rank = 0
        severity_map = {0: "NONE", 1: "LOW", 2: "MEDIUM", 3: "HIGH"}
        rank_lookup = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

        congested_segments = []
        for i, node_id in enumerate(path_nodes):
            node_data = nx_g.nodes.get(node_id, {})
            lat = node_data.get('lat', node_data.get('y', 0.0))
            lon = node_data.get('lon', node_data.get('x', 0.0))

            if lat is not None and lon is not None:
                lat_f, lon_f = float(lat), float(lon)
                geometry.append([lat_f, lon_f])
                nodes_out.append({"id": str(node_id), "lat": lat_f, "lon": lon_f})
            else:
                nodes_out.append({"id": str(node_id), "lat": 0.0, "lon": 0.0})

            if i < len(path_nodes) - 1:
                next_id = path_nodes[i + 1]
                edge_data_map = nx_g.get_edge_data(node_id, next_id) or {}

                best_key, best_edge, best_tt = 0, {}, float("inf")
                if isinstance(edge_data_map, dict):
                    for k, ed in edge_data_map.items():
                        tt = float(ed.get('travel_time', ed.get('length', 0.0)) or 0.0)
                        if tt < best_tt:
                            best_tt, best_key, best_edge = tt, k, ed

                length_raw = float(best_edge.get('length', best_edge.get('distance', 0.0)) or 0.0)
                if length_raw > 50:
                    length_raw /= 1000.0
                time_sec = float(best_edge.get('travel_time', 0.0) or (length_raw * 60.0))

                total_dist_km += length_raw
                total_time_sec += time_sec
                total_base_cost += time_sec

                if routing_mode == "traffic_aware":
                    e_key1 = f"{node_id}-{next_id}-{best_key}"
                    e_key2 = f"{node_id}-{next_id}-0"
                    cost_info = traffic_costs_map.get(e_key1) or traffic_costs_map.get(e_key2) or traffic_costs_map.get((str(node_id), str(next_id)))

                    if cost_info:
                        p_factor = cost_info.get("penalty_factor", 1.0)
                        t_penalty = time_sec * (p_factor - 1.0)
                        t_level = cost_info.get("traffic_level", "NONE")
                    else:
                        t_penalty = 0.0
                        t_level = "NONE"
                else:
                    t_penalty = 0.0
                    t_level = "NONE"

                total_traffic_penalty += t_penalty
                sev_r = rank_lookup.get(t_level, 0)
                if sev_r > max_severity_rank:
                    max_severity_rank = sev_r

                if sev_r >= 2:  # MEDIUM or HIGH
                    u_node = nx_g.nodes.get(node_id, {})
                    v_node = nx_g.nodes.get(next_id, {})
                    u_lat = float(u_node.get('lat', u_node.get('y', 0.0)) or 0.0)
                    u_lon = float(u_node.get('lon', u_node.get('x', 0.0)) or 0.0)
                    v_lat = float(v_node.get('lat', v_node.get('y', 0.0)) or 0.0)
                    v_lon = float(v_node.get('lon', v_node.get('x', 0.0)) or 0.0)
                    congested_segments.append({
                        "source": str(node_id),
                        "target": str(next_id),
                        "traffic_level": t_level,
                        "coords": [[u_lat, u_lon], [v_lat, v_lon]]
                    })

                edges_out.append({
                    "source": str(node_id),
                    "target": str(next_id),
                    "key": best_key,
                    "length": round(length_raw, 6),
                    "travel_time": round(time_sec, 4),
                    "speed_limit": float(best_edge.get("speed_limit", 0.0) or 0.0),
                    "highway": str(best_edge.get("highway", "road")),
                    "oneway": bool(best_edge.get("oneway", False)),
                })

        total_dist_km = round(total_dist_km, 3)
        total_time_sec = round(total_time_sec, 1)
        eta_minutes = round(total_time_sec / 60.0, 1)
        base_cost_val = round(total_base_cost, 1)
        traffic_cost_val = round(total_traffic_penalty, 1)
        total_cost_val = round(total_base_cost + total_traffic_penalty, 1)
        traffic_level_val = severity_map[max_severity_rank]

        return {
            "geometry": geometry,
            "nodes_out": nodes_out,
            "edges_out": edges_out,
            "distance_km": total_dist_km,
            "travel_time_seconds": total_time_sec,
            "eta_minutes": eta_minutes,
            "base_cost": base_cost_val,
            "traffic_cost": traffic_cost_val,
            "total_cost": total_cost_val,
            "traffic_level": traffic_level_val,
            "congested_segments": congested_segments,
        }

    def compare_algorithms(
        self,
        source_node,
        destination_node,
        source_lat=None,
        source_lon=None,
        destination_lat=None,
        destination_lon=None,
        weight="travel_time",
        routing_mode="normal"
    ):
        """
        Runs both A* and Dijkstra on the identical cached graph instance.
        Evaluates Sprint 10 recommendations.
        """
        old_status = route_store.get_reroute_status()
        route_store.set_reroute_status("comparison_mode")
        
        astar_res = {"success": False, "error": "Unknown error"}
        try:
            astar_res = self.calculate_route(
                source_node=source_node,
                destination_node=destination_node,
                algorithm="astar",
                source_lat=source_lat,
                source_lon=source_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                weight=weight,
                routing_mode=routing_mode
            )
        except Exception as exc:
            astar_res["error"] = str(exc)

        dijkstra_res = {"success": False, "error": "Unknown error"}
        try:
            dijkstra_res = self.calculate_route(
                source_node=source_node,
                destination_node=destination_node,
                algorithm="dijkstra",
                source_lat=source_lat,
                source_lon=source_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                weight=weight,
                routing_mode=routing_mode
            )
        except Exception as exc:
            dijkstra_res["error"] = str(exc)
            
        route_store.set_reroute_status(old_status)

        recommendation = self._determine_recommendation(astar_res, dijkstra_res)
        
        # Set active route to recommended if possible
        if recommendation["algorithm"] == "astar" and astar_res.get("success"):
            route_store.set_route({
                "path_nodes": [n["id"] for n in astar_res["nodes"]],
                "geometry": astar_res["geometry"],
                "source_node_id": astar_res["source_node"],
                "target_node_id": astar_res["destination_node"],
                "total_distance_km": astar_res["distance_km"],
                "total_duration_seconds": astar_res["travel_time_seconds"],
                "total_cost": astar_res["total_cost"]
            }, algorithm="astar", routing_mode=routing_mode)
        elif recommendation["algorithm"] == "dijkstra" and dijkstra_res.get("success"):
            route_store.set_route({
                "path_nodes": [n["id"] for n in dijkstra_res["nodes"]],
                "geometry": dijkstra_res["geometry"],
                "source_node_id": dijkstra_res["source_node"],
                "target_node_id": dijkstra_res["destination_node"],
                "total_distance_km": dijkstra_res["distance_km"],
                "total_duration_seconds": dijkstra_res["travel_time_seconds"],
                "total_cost": dijkstra_res["total_cost"]
            }, algorithm="dijkstra", routing_mode=routing_mode)

        return {
            "status": "success",
            "success": True,
            "source_node": str(source_node),
            "destination_node": str(destination_node),
            "routing_mode": routing_mode,
            "comparison": {
                "astar": astar_res,
                "dijkstra": dijkstra_res
            },
            "recommendation": recommendation
        }

    def _determine_recommendation(self, astar_res, dijkstra_res):
        a_ok = astar_res.get("success", False)
        d_ok = dijkstra_res.get("success", False)

        if not a_ok and not d_ok:
            return {"algorithm": "none", "reason": "Both routing algorithms failed to calculate a path."}
        if not a_ok:
            return {"algorithm": "dijkstra", "reason": "Dijkstra is recommended because A* Search failed."}
        if not d_ok:
            return {"algorithm": "astar", "reason": "A* Search is recommended because Dijkstra failed."}

        # Both succeeded. Extract metrics.
        cost_a = astar_res.get("total_cost", 0.0)
        cost_d = dijkstra_res.get("total_cost", 0.0)

        eta_a = astar_res.get("eta_minutes", 0.0)
        eta_d = dijkstra_res.get("eta_minutes", 0.0)

        dist_a = astar_res.get("distance_km", 0.0)
        dist_d = dijkstra_res.get("distance_km", 0.0)

        time_a = astar_res.get("execution_time_ms")
        time_d = dijkstra_res.get("execution_time_ms")

        nodes_a = astar_res.get("nodes_explored")
        nodes_d = dijkstra_res.get("nodes_explored")

        # FIRST: Compare traffic-adjusted total cost (significant difference > 0.1)
        if cost_a < cost_d - 0.1:
            return {"algorithm": "astar", "reason": f"A* Search is recommended because it has the lower traffic-adjusted route cost ({cost_a} vs {cost_d})."}
        elif cost_d < cost_a - 0.1:
            return {"algorithm": "dijkstra", "reason": f"Dijkstra is recommended because it has the lower traffic-adjusted route cost ({cost_d} vs {cost_a})."}

        # SECOND: Compare ETA (significant difference > 0.1 min)
        if eta_a < eta_d - 0.1:
            return {"algorithm": "astar", "reason": f"A* Search is recommended because both routes have similar cost, but A* Search has lower ETA ({eta_a} min vs {eta_d} min)."}
        elif eta_d < eta_a - 0.1:
            return {"algorithm": "dijkstra", "reason": f"Dijkstra is recommended because both routes have similar cost, but Dijkstra has lower ETA ({eta_d} min vs {eta_a} min)."}

        # THIRD: Compare Distance (significant difference > 0.05 km)
        if dist_a < dist_d - 0.05:
            return {"algorithm": "astar", "reason": f"A* Search is recommended because route cost and ETA are similar, but A* Search offers a shorter distance ({dist_a} km vs {dist_d} km)."}
        elif dist_d < dist_a - 0.05:
            return {"algorithm": "dijkstra", "reason": f"Dijkstra is recommended because route cost and ETA are similar, but Dijkstra offers a shorter distance ({dist_d} km vs {dist_a} km)."}

        # FOURTH: Performance tie-breaker — Execution Time (difference > 0.5 ms)
        if time_a is not None and time_d is not None:
            if time_a < time_d - 0.5:
                return {"algorithm": "astar", "reason": f"Both algorithms produced equivalent routes. A* Search completed faster ({time_a} ms vs {time_d} ms)."}
            elif time_d < time_a - 0.5:
                return {"algorithm": "dijkstra", "reason": f"Both algorithms produced equivalent routes. Dijkstra completed faster ({time_d} ms vs {time_a} ms)."}

        # FIFTH: Performance tie-breaker — Nodes Explored
        if nodes_a is not None and nodes_d is not None:
            if nodes_a < nodes_d:
                return {"algorithm": "astar", "reason": f"Both algorithms produced equivalent routes. A* Search explored fewer nodes ({nodes_a} vs {nodes_d})."}
            elif nodes_d < nodes_a:
                return {"algorithm": "dijkstra", "reason": f"Both algorithms produced equivalent routes. Dijkstra explored fewer nodes ({nodes_d} vs {nodes_a})."}

        # Fallback default
        return {"algorithm": "astar", "reason": "Both algorithms found identical routes with equal performance. A* Search is selected as default."}

    def evaluate_reroute(self):
        """
        Evaluate the currently active route against live traffic conditions for Sprint 11.
        Returns a recommendation structure.
        """
        logger = self._get_logger()
        active_r = route_store.get_route()
        if not active_r:
            return {"recommended": False, "reroute_available": False, "status": "NO_CHANGE", "reason": "No active route"}

        routing_mode = route_store.get_routing_mode()

        # Cooldown check
        last_t = route_store.get_last_reroute_time()
        cooldown = current_app.config.get("REROUTE_COOLDOWN_SECONDS", 15.0)
        elapsed = time.time() - last_t
        if elapsed < cooldown:
            logger.info("[REROUTE] REROUTE_SKIPPED_COOLDOWN: cooldown active (%.1fs remaining)", cooldown - elapsed)
            return {
                "recommended": False,
                "reroute_available": False,
                "status": "COOLDOWN",
                "reason": f"Reroute cooldown active ({round(cooldown - elapsed)}s remaining)"
            }

        logger.info("[REROUTE] ROUTE_MONITOR_STARTED: evaluating active route")

        nx_g = graph_service.get_nx_graph_safe()
        if not nx_g:
            logger.warning("[REROUTE] REROUTE_EVALUATION_FAILED: Graph not loaded")
            return {"recommended": False, "reroute_available": False, "status": "ERROR", "reason": "Graph not loaded"}

        # Get traffic costs map
        traffic_costs_map = {}
        try:
            from app.modules.traffic_intelligence.services.traffic_cost_service import traffic_cost_service
            tc_data = traffic_cost_service.get_cached_costs()
            if tc_data and tc_data.get("success", False):
                for cost_item in tc_data.get("edge_costs", []):
                    e_key = cost_item.get("edge_id")
                    traffic_costs_map[e_key] = cost_item
                    src_str = str(cost_item.get("source_node"))
                    tgt_str = str(cost_item.get("target_node"))
                    traffic_costs_map[(src_str, tgt_str)] = cost_item
        except Exception as exc:
            logger.warning("[REROUTE] REROUTE_EVALUATION_FAILED: Failed to retrieve live traffic costs: %s", exc)

        path_nodes = active_r.get("path_nodes")
        if not path_nodes or len(path_nodes) < 2:
            return {"recommended": False, "reroute_available": False, "status": "NO_CHANGE", "reason": "Active route too short"}

        try:
            current_metrics = self._calculate_path_metrics(nx_g, path_nodes, traffic_costs_map, routing_mode="traffic_aware")
        except Exception as exc:
            logger.warning("[REROUTE] REROUTE_EVALUATION_FAILED: Failed to calculate path metrics: %s", exc)
            return {"recommended": False, "reroute_available": False, "status": "ERROR", "reason": "Failed to calculate current path metrics"}

        current_cost = current_metrics["total_cost"]
        current_eta = current_metrics["eta_minutes"]
        current_level = current_metrics["traffic_level"]

        route_store.set_current_cost(current_cost)
        route_store.set_last_evaluation_time(time.time())

        # Retrieve thresholds
        min_cost_inc = current_app.config.get("MIN_TRAFFIC_COST_INCREASE_PERCENT", 0.15)
        min_eta_inc = current_app.config.get("MIN_ETA_INCREASE_PERCENT", 0.15)
        min_traffic_lvl = current_app.config.get("MIN_TRAFFIC_CHANGE_LEVEL", "MEDIUM")
        min_improvement = current_app.config.get("MIN_ROUTE_IMPROVEMENT_PERCENT", 0.05)
        min_divergence = current_app.config.get("MIN_ROUTE_DIVERGENCE_PERCENT", 0.10)

        original_cost = route_store.get_original_cost()
        original_eta = active_r.get("eta_minutes") or (original_cost / 60.0)
        original_level = active_r.get("traffic_level", "NONE")

        # Hotspot checking
        hotspot_affects_route = False
        affected_hotspot_id = None
        try:
            from app.modules.traffic_intelligence.services.hotspot_service import hotspot_service
            hotspots_res = hotspot_service.detect_hotspots()
            if hotspots_res and hotspots_res.get("success", False):
                hotspots = hotspots_res.get("hotspots", [])
                for h in hotspots:
                    if h.get("severity") in ["MEDIUM", "HIGH"]:
                        h_lat = h.get("center_latitude")
                        h_lon = h.get("center_longitude")
                        h_rad_km = h.get("radius_meters", 200.0) / 1000.0
                        
                        geom = current_metrics.get("geometry") or []
                        for pt in geom:
                            pt_lat, pt_lon = pt[0], pt[1]
                            dist = haversine_distance(pt_lat, pt_lon, h_lat, h_lon)
                            if dist <= h_rad_km:
                                hotspot_affects_route = True
                                affected_hotspot_id = h.get("hotspot_id")
                                break
                    if hotspot_affects_route:
                        break
        except Exception as exc:
            logger.warning("[REROUTE] Failed to detect hotspots: %s", exc)

        # Degradation checks
        route_degraded = False
        degradation_reason = ""

        # A. Cost degradation
        if original_cost > 0:
            cost_increase_pct = (current_cost - original_cost) / original_cost
            if cost_increase_pct >= min_cost_inc:
                route_degraded = True
                degradation_reason = f"Route traffic-adjusted cost increased by {round(cost_increase_pct * 100, 1)}%"

        # B. ETA degradation
        if not route_degraded and original_eta > 0:
            eta_increase_pct = (current_eta - original_eta) / original_eta
            if eta_increase_pct >= min_eta_inc:
                route_degraded = True
                degradation_reason = f"Route ETA increased by {round(eta_increase_pct * 100, 1)}%"

        # C. Traffic severity degradation
        if not route_degraded:
            rank_lookup = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
            orig_rank = rank_lookup.get(original_level, 0)
            curr_rank = rank_lookup.get(current_level, 0)
            min_change_rank = rank_lookup.get(min_traffic_lvl, 2)
            if curr_rank > orig_rank and curr_rank >= min_change_rank:
                route_degraded = True
                degradation_reason = f"Route traffic severity worsened from {original_level} to {current_level}"

        # D. Hotspot degradation
        if not route_degraded and hotspot_affects_route:
            route_degraded = True
            degradation_reason = f"Route is affected by traffic hotspot {affected_hotspot_id}"

        if not route_degraded:
            return {
                "recommended": False,
                "reroute_available": False,
                "status": "MONITORING",
                "reason": "Current route is stable and within acceptable limits.",
                "current_route": {
                    "distance_km": current_metrics["distance_km"],
                    "traffic_cost": current_metrics["traffic_cost"],
                    "eta_minutes": current_metrics["eta_minutes"],
                    "traffic_level": current_metrics["traffic_level"],
                    "congested_segments": current_metrics.get("congested_segments", [])
                }
            }

        # Route is degraded!
        logger.info("[REROUTE] TRAFFIC_CHANGE_DETECTED: traffic cost or severity changed")
        logger.info("[REROUTE] ROUTE_DEGRADED: %s", degradation_reason)
        logger.info("[REROUTE] REROUTE_EVALUATION_STARTED: searching for alternative routes")

        start_time_ms = time.time() * 1000.0
        src = path_nodes[0]
        tgt = path_nodes[-1]
        penalty_base = current_app.config.get("REROUTE_EDGE_PENALTY_FACTOR", 5.0)

        active_route_edges_count = len(path_nodes) - 1
        congested_edges_count = 0

        # Build congestion penalties for active route
        congested_edges_base = {}
        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i+1]
            e_key_0 = f"{u}-{v}-0"
            cost_info = traffic_costs_map.get(e_key_0) or traffic_costs_map.get((str(u), str(v)))
            lvl = cost_info.get("traffic_level") if cost_info else "NONE"
            if lvl == "HIGH":
                congested_edges_count += 1
                congested_edges_base[e_key_0] = penalty_base
                congested_edges_base[(str(u), str(v))] = penalty_base
            elif lvl == "MEDIUM":
                congested_edges_count += 1
                congested_edges_base[e_key_0] = penalty_base * 0.6
                congested_edges_base[(str(u), str(v))] = penalty_base * 0.6

        # Candidate configurations evaluating BOTH A* and Dijkstra
        candidate_configs = [
            {"algo": "astar", "penalty_mult": 1.0},
            {"algo": "dijkstra", "penalty_mult": 1.0},
            {"algo": "astar", "penalty_mult": 1.6},
            {"algo": "dijkstra", "penalty_mult": 1.6},
            {"algo": "astar", "penalty_mult": 2.5},
            {"algo": "dijkstra", "penalty_mult": 2.5},
        ]

        color_palette = ["#22c55e", "#06b6d4", "#a855f7"]
        label_palette = ["Recommended", "Alternative 2", "Alternative 3"]

        old_status = route_store.get_reroute_status()
        route_store.set_reroute_status("rerouting_evaluation")

        prev_r = route_store.get_previous_route()
        prev_geom = (prev_r.get("geometry") or []) if prev_r else []
        max_dist_inc = current_app.config.get("MAX_ACCEPTABLE_DISTANCE_INCREASE_PERCENT", 1.50)

        raw_candidates = []
        astar_count = 0
        dijkstra_count = 0
        duplicates_removed = 0
        low_diversity_removed = 0

        # Execute dual-algorithm search in parallel with bounded timeout (30s)
        import concurrent.futures
        ALTERNATIVE_SEARCH_TIMEOUT = 30.0

        def _calc_candidate(cfg):
            penalties = dict(congested_edges_base)
            for k in penalties:
                penalties[k] *= cfg["penalty_mult"]
            return cfg["algo"], self.calculate_route(
                source_node=src,
                destination_node=tgt,
                algorithm=cfg["algo"],
                routing_mode="traffic_aware",
                reroute_penalties=penalties
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(candidate_configs)) as executor:
                futures = {executor.submit(_calc_candidate, cfg): cfg for cfg in candidate_configs}
                for future in concurrent.futures.as_completed(futures, timeout=ALTERNATIVE_SEARCH_TIMEOUT):
                    try:
                        algo_used, alt = future.result()
                        if alt and alt.get("success", False):
                            raw_candidates.append((algo_used, alt))
                            if algo_used == "astar":
                                astar_count += 1
                            else:
                                dijkstra_count += 1
                    except Exception as fe:
                        logger.warning("[REROUTE] Candidate subtask error: %s", fe)
        except concurrent.futures.TimeoutError:
            logger.warning("[REROUTE] Alternative search exceeded 30s timeout; proceeding with collected candidates.")
        except Exception as exc:
            logger.warning("[REROUTE] Parallel reroute search error: %s", exc)
        finally:
            route_store.set_reroute_status(old_status)

        total_candidates_count = len(raw_candidates)

        # Diversity & Quality Filtering
        curr_node_ids = set(str(n) for n in path_nodes)
        curr_geom_tuples = set((round(pt[0], 6), round(pt[1], 6)) for pt in (current_metrics.get("geometry") or []))

        candidate_routes = []
        seen_geometries = [curr_geom_tuples]

        for algo_used, alt in raw_candidates:
            if len(candidate_routes) >= 3:
                break

            alt_cost = alt.get("total_cost", 0)
            alt_dist = alt.get("distance_km", 0.0)
            alt_nodes = alt.get("nodes", [])
            alt_node_ids = set(str(n["id"]) for n in alt_nodes)
            alt_geom = alt.get("geometry") or []
            alt_geom_tuples = set((round(pt[0], 6), round(pt[1], 6)) for pt in alt_geom)

            # 1. Duplicate geometry check
            is_dup = False
            for sg in seen_geometries:
                if len(alt_geom_tuples) > 0 and len(alt_geom_tuples.symmetric_difference(sg)) == 0:
                    is_dup = True
                    break
            if is_dup:
                duplicates_removed += 1
                logger.info("[REROUTE] Candidate rejected: exact duplicate route geometry")
                continue

            # 2. Divergence against current active route
            shared_curr = len(alt_node_ids.intersection(curr_node_ids))
            total_alt = len(alt_node_ids)
            divergence_curr = 1.0 - (shared_curr / total_alt) if total_alt > 0 else 0.0

            if divergence_curr < min_divergence:
                low_diversity_removed += 1
                logger.info("[REROUTE] Candidate rejected: insufficient divergence from current route (%.2f < %.2f)", divergence_curr, min_divergence)
                continue

            # 3. Mutual divergence against existing accepted candidates
            is_mutually_diverse = True
            for existing_cand in candidate_routes:
                e_node_ids = set(str(n) for n in existing_cand.get("path_nodes", []))
                shared_cand = len(alt_node_ids.intersection(e_node_ids))
                div_cand = 1.0 - (shared_cand / total_alt) if total_alt > 0 else 0.0
                if div_cand < min_divergence:
                    is_mutually_diverse = False
                    break

            if not is_mutually_diverse:
                low_diversity_removed += 1
                logger.info("[REROUTE] Candidate rejected: insufficient mutual divergence from existing candidates")
                continue

            # 4. Distance increase protection check
            if current_metrics["distance_km"] > 0:
                dist_inc_pct = (alt_dist - current_metrics["distance_km"]) / current_metrics["distance_km"]
                if dist_inc_pct > max_dist_inc:
                    logger.info("[REROUTE] Candidate rejected: distance increase too high (%.1f%% > %.1f%%)", dist_inc_pct * 100, max_dist_inc * 100)
                    continue

            # 5. Improvement calculation & loop protection
            improvement = (current_cost - alt_cost) / current_cost if current_cost > 0 else 0.0
            is_loop = (prev_geom == alt_geom)
            effective_min_imp = min_improvement * 2.0 if is_loop else min_improvement

            if improvement < effective_min_imp:
                logger.info("[REROUTE] Candidate rejected: insufficient cost improvement (%.1f%% < %.1f%%)", improvement * 100, effective_min_imp * 100)
                continue

            seen_geometries.append(alt_geom_tuples)
            c_idx = len(candidate_routes)
            candidate_obj = {
                **alt,
                "id": f"alt_candidate_{c_idx + 1}",
                "algorithm": algo_used,
                "distance_km": alt.get("distance_km"),
                "traffic_cost": alt.get("traffic_cost"),
                "total_cost": alt.get("total_cost"),
                "eta_minutes": alt.get("eta_minutes"),
                "traffic_level": alt.get("traffic_level"),
                "path_nodes": [str(n["id"]) for n in alt.get("nodes", [])],
                "source_node_id": src,
                "target_node_id": tgt,
                "improvement_percent": round(improvement * 100, 1),
                "divergence_percent": round(divergence_curr * 100, 1),
                "color": color_palette[c_idx],
                "label": label_palette[c_idx]
            }
            candidate_routes.append(candidate_obj)

        search_time_ms = round(time.time() * 1000.0 - start_time_ms, 1)

        # Structured summary log
        logger.info(
            "ACTIVE ROUTE EDGES: %d | CONGESTED EDGES: %d | A* CANDIDATES: %d | DIJKSTRA CANDIDATES: %d | TOTAL CANDIDATES: %d | DUPLICATES REMOVED: %d | LOW-DIVERSITY REMOVED: %d | FINAL ALTERNATIVES: %d | SEARCH TIME: %.1f ms",
            active_route_edges_count, congested_edges_count, astar_count, dijkstra_count, total_candidates_count, duplicates_removed, low_diversity_removed, len(candidate_routes), search_time_ms
        )

        if not candidate_routes:
            logger.info("[REROUTE] REROUTE_EVALUATION_FAILED: No valid alternative candidate routes found")
            return {
                "recommended": False,
                "reroute_available": False,
                "status": "NO_BETTER_ROUTE",
                "reason": "Heavy traffic detected on active route, but no significantly better alternative route was found.",
                "search_time_ms": search_time_ms,
                "algorithms_evaluated": ["astar", "dijkstra"],
                "current_route": {
                    "distance_km": current_metrics["distance_km"],
                    "traffic_cost": current_metrics["traffic_cost"],
                    "eta_minutes": current_metrics["eta_minutes"],
                    "traffic_level": current_metrics["traffic_level"],
                    "congested_segments": current_metrics.get("congested_segments", [])
                },
                "alternatives": [],
                "recommended_route": None
            }

        # Sort candidate routes by total_cost (lowest first)
        candidate_routes.sort(key=lambda c: c.get("total_cost", float("inf")))
        for i, c in enumerate(candidate_routes):
            c["color"] = color_palette[i]
            c["label"] = label_palette[i]

        best_alt = candidate_routes[0]
        top_imp = best_alt.get("improvement_percent", 0.0)

        logger.info("[REROUTE] ALTERNATIVE_ROUTES_FOUND: %d candidate(s) found. Best improvement: %.1f%%", len(candidate_routes), top_imp)
        return {
            "recommended": True,
            "reroute_available": True,
            "status": "REROUTE_AVAILABLE",
            "reason": f"Traffic has increased on your route. Found {len(candidate_routes)} alternative path(s). Best alternative is {top_imp}% faster.",
            "search_time_ms": search_time_ms,
            "algorithms_evaluated": ["astar", "dijkstra"],
            "current_route": {
                "distance_km": current_metrics["distance_km"],
                "traffic_cost": current_metrics["traffic_cost"],
                "eta_minutes": current_metrics["eta_minutes"],
                "traffic_level": current_metrics["traffic_level"],
                "congested_segments": current_metrics.get("congested_segments", [])
            },
            "recommended_route": best_alt,
            "alternative_route": best_alt,
            "alternative_routes": candidate_routes,
            "alternatives": candidate_routes,
            "improvement_percent": top_imp
        }


# Singleton instance
routing_service = RoutingService()
