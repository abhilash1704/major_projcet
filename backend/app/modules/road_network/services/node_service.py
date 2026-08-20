"""
node_service.py — RouteFlow Nearest Node Lookup Service

Uses the pre-built cKDTree spatial index from graph_service for O(log N)
nearest-node queries instead of a linear O(N) scan over 517k nodes.

The spatial index is built ONCE when the graph loads on backend startup.
It is never rebuilt per request.
"""

import logging
from flask import current_app

from ..utils.geo_utils import haversine_distance, is_valid_coordinate
from ..constants import MAX_SNAP_DISTANCE_KM
from ..services.graph_service import graph_service


from collections import OrderedDict
import logging
from flask import current_app

from ..utils.geo_utils import haversine_distance
from ..services.graph_service import graph_service

PROGRESSIVE_RADII_KM = [0.025, 0.050, 0.100, 0.250, 0.500, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0]
MAX_SEARCH_RADIUS_KM = 20.0
LRU_CACHE_CAPACITY = 1000


class NodeService:
    """
    Service responsible for spatial queries on road network nodes.
    Implements progressive 20 KM radius search, graph connectivity validation,
    coordinate validation, and bounded LRU caching.
    """

    def __init__(self):
        self._lookup_cache = OrderedDict()

    def _get_logger(self):
        try:
            if current_app and hasattr(current_app, 'logger') and current_app.logger:
                return current_app.logger
        except Exception:
            pass
        return logging.getLogger("routeflow.road_network.node")

    def _validate_coords(self, lat_val, lon_val):
        """Validates coordinates and detects accidental swaps."""
        try:
            lat = float(lat_val)
            lon = float(lon_val)
        except (ValueError, TypeError):
            return None, None, "Invalid numeric coordinate format."

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            if (-90.0 <= lon <= 90.0) and (-180.0 <= lat <= 180.0):
                if abs(lat) > 90.0:
                    return None, None, "Detected swapped coordinates: latitude out of range [-90, 90]."
            return None, None, "Coordinates out of geographic range [-90, 90] and [-180, 180]."

        return lat, lon, None

    def find_nearest_node(self, latitude, longitude, graph=None, max_distance_km=None):
        logger = self._get_logger()
        logger.info("Nearest node search requested for coordinates (lat: %s, lon: %s)", latitude, longitude)

        # Coordinate Validation
        lat, lon, err_msg = self._validate_coords(latitude, longitude)
        if err_msg or lat is None or lon is None:
            logger.warning("Coordinate validation failed for (%s, %s): %s", latitude, longitude, err_msg)
            return {
                "success": False,
                "found": False,
                "error": "INVALID_COORDINATES",
                "reason": "INVALID_COORDINATES",
                "message": err_msg or "Location coordinates are invalid.",
            }

        # Bounded LRU Cache lookup (5 decimal places ~1.1m precision)
        cache_key = (round(lat, 5), round(lon, 5))
        if cache_key in self._lookup_cache:
            self._lookup_cache.move_to_end(cache_key)
            return self._lookup_cache[cache_key]

        threshold_km = float(max_distance_km) if max_distance_km else MAX_SEARCH_RADIUS_KM

        # Auto-load matching regional graph from cache if coordinates are outside active graph bounds
        if graph is None:
            graph_service.ensure_graph_for_location(lat, lon)

        nx_g = graph or graph_service.get_nx_graph()
        if nx_g is None or len(nx_g) == 0:
            return {
                "success": False,
                "found": False,
                "error": "NO_GRAPH_LOADED",
                "reason": "SERVICE_UNAVAILABLE",
                "message": "Road network service is temporarily unavailable.",
            }

        # Progressive search across radii
        active_radii = [r for r in PROGRESSIVE_RADII_KM if r <= threshold_km]
        if not active_radii or active_radii[-1] < threshold_km:
            active_radii.append(threshold_km)

        selected_node = None
        selected_dist = float('inf')
        search_radius_used = 0.0

        for radius in active_radii:
            # Query candidate road nodes within current bounding ball radius
            candidates = graph_service.find_candidates_in_radius(lat, lon, radius)
            valid_candidates = []

            for cand in candidates:
                nid = cand["node_id"]
                # Graph Validation: must exist in graph AND have valid connections (degree > 0)
                if nid in nx_g:
                    try:
                        deg = nx_g.degree(nid)
                    except Exception:
                        deg = 1
                    if deg > 0:
                        valid_candidates.append(cand)

            if valid_candidates:
                # Select nearest valid node and STOP immediately
                best = valid_candidates[0]  # already sorted by distance_km ascending
                selected_node = best
                selected_dist = best["distance_km"]
                search_radius_used = radius
                break

        if selected_node and selected_dist <= threshold_km:
            nid = selected_node["node_id"]
            n_lat = selected_node["latitude"]
            n_lon = selected_node["longitude"]
            res = {
                "success": True,
                "found": True,
                "node_id": nid,
                "latitude": n_lat,
                "longitude": n_lon,
                "distance_km": selected_dist,
                "search_radius_km": search_radius_used,
                "node": {
                    "node_id": nid,
                    "latitude": n_lat,
                    "longitude": n_lon,
                }
            }
            # Cache result
            self._lookup_cache[cache_key] = res
            if len(self._lookup_cache) > LRU_CACHE_CAPACITY:
                self._lookup_cache.popitem(last=False)
            return res

        # 20 KM HARD LIMIT reached with no valid node
        controlled_result = {
            "success": False,
            "found": False,
            "error": "LOCATION_OUTSIDE_ROAD_NETWORK",
            "reason": "OUTSIDE_NETWORK_COVERAGE",
            "message": "Location is outside the available road network.",
            "max_search_radius_km": int(MAX_SEARCH_RADIUS_KM),
        }
        return controlled_result

    def find_nodes_in_radius(self, latitude, longitude, radius_km=None, graph=None):
        """
        Finds all RoadNodes within a given radius (km) of (latitude, longitude).
        Uses the RoadGraph node collection (preserved for backward compat).
        """
        logger = self._get_logger()
        from ..constants import DEFAULT_SEARCH_RADIUS_KM
        search_radius = radius_km or DEFAULT_SEARCH_RADIUS_KM
        logger.info("Radius node search for coordinates (%s, %s) within %.2f km",
                    latitude, longitude, search_radius)

        if not is_valid_coordinate(latitude, longitude):
            return []

        target_graph = graph or graph_service._active_graph
        if not target_graph or not getattr(target_graph, 'nodes', None):
            return []

        lat = float(latitude)
        lon = float(longitude)
        matching_nodes = []

        for node in target_graph.nodes.values():
            if node.latitude is None or node.longitude is None:
                continue
            dist = haversine_distance(lat, lon, node.latitude, node.longitude)
            if dist <= search_radius:
                matching_nodes.append({
                    "node": node.to_dict(),
                    "distance_km": round(dist, 4)
                })

        matching_nodes.sort(key=lambda x: x["distance_km"])
        return matching_nodes


node_service = NodeService()
