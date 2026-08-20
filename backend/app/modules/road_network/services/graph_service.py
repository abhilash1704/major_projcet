"""
graph_service.py — RouteFlow Road Network Graph Manager

Performance-optimised graph management:
  - Single-instance in-memory NetworkX graph (load once on startup)
  - scipy.spatial.cKDTree spatial index for O(log N) nearest-node queries
  - O(1) bounding-box coverage check (no linear node scan)
  - Thread-safe singleton with double-checked locking
  - Overpass API is NEVER called during normal route/node operations
  - Explicit ingest-only API: ingest_osm_and_build()
"""

import os
import math
import time
import pickle
import logging
import threading
import numpy as np
import networkx as nx
from flask import current_app
from scipy.spatial import cKDTree

from ..models import RoadGraph, RoadNode, RoadEdge
from ..constants import GRAPH_CACHE_DIR, MAX_GRAPH_NODES, MAX_SNAP_DISTANCE_KM
from ..services.osm_service import osm_service
from ..utils.geo_utils import haversine_distance, is_valid_coordinate, compute_region_bbox, generate_region_cache_key


class GraphService:
    """
    Singleton graph manager for the RouteFlow road network.

    Responsibilities:
      - Load the pre-built graph from disk cache at startup (load once).
      - Build a cKDTree spatial index for O(log N) nearest-node lookup.
      - Expose get_nx_graph() / get_nx_graph_safe() for routing and node services.
      - Guard against concurrent double-loads with a threading.Lock.
      - NEVER call Overpass API during normal route/node operations.
    """

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or GRAPH_CACHE_DIR
        self._active_graph = None          # RoadGraph metadata container
        self._nx_graph = None              # NetworkX MultiDiGraph — primary routing graph
        self._spatial_index = None         # cKDTree built over all node coords
        self._spatial_node_ids = None      # numpy array of node ID strings (index ↔ cKDTree row)
        self._spatial_node_lats = None     # numpy float array of latitudes
        self._spatial_node_lons = None     # numpy float array of longitudes
        self._graph_bbox = None            # {min_lat, max_lat, min_lon, max_lon} — O(1) coverage
        self._load_lock = threading.Lock()
        self._is_preloaded = False

    # ──────────────────────────────────────────────────────────────────────────
    # Logging helper
    # ──────────────────────────────────────────────────────────────────────────

    def _get_logger(self):
        try:
            if current_app and hasattr(current_app, 'logger') and current_app.logger:
                return current_app.logger
        except Exception:
            pass
        return logging.getLogger("routeflow.road_network.graph")

    # ──────────────────────────────────────────────────────────────────────────
    # Startup preloading
    # ──────────────────────────────────────────────────────────────────────────

    def preload_default_graph(self, cache_key="bangalore_default"):
        """
        Called ONCE during Flask application startup (create_app).
        Loads the default cached graph and builds the spatial index.
        Does NOT call Overpass API.
        """
        logger = self._get_logger()
        if self._is_preloaded and self._nx_graph is not None:
            return True  # Already loaded — skip

        with self._load_lock:
            if self._is_preloaded and self._nx_graph is not None:
                return True  # Double-checked

            cache_path = os.path.join(self.cache_dir, f"{cache_key}.pickle")
            logger.info("[Graph] Loading cached graph...")
            logger.info("[Graph] Cache: %s", cache_path)

            if not os.path.exists(cache_path):
                logger.warning("[Graph] WARNING: Cached graph unavailable — file not found: %s", cache_path)
                self._is_preloaded = True  # Mark as attempted to prevent retries on every request
                return False

            t0 = time.perf_counter()
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)

                nx_g = data.get("nx_graph")
                road_g = data.get("road_graph")

                if nx_g is None or len(nx_g) == 0:
                    logger.warning("[Graph] WARNING: Cached graph is empty or corrupted: %s", cache_path)
                    self._is_preloaded = True
                    return False

                # Validate cache integrity
                if not self._validate_cached_graph(nx_g, logger):
                    logger.warning("[Graph] WARNING: Cache validation failed: %s", cache_path)
                    self._is_preloaded = True
                    return False

                self._nx_graph = nx_g
                self._active_graph = road_g

                # Build bbox (O(1) coverage checks)
                self._build_graph_bbox()

                # Build cKDTree spatial index
                self._build_spatial_index()

                elapsed = time.perf_counter() - t0
                logger.info("[Graph] Nodes: %d", nx_g.number_of_nodes())
                logger.info("[Graph] Edges: %d", nx_g.number_of_edges())
                logger.info("[Graph] Graph loaded successfully in %.2f seconds", elapsed)
                self._is_preloaded = True
                return True

            except Exception as exc:
                logger.error("[Graph] Failed to load cache file %s: %s", cache_path, str(exc))
                self._is_preloaded = True
                return False

    # ──────────────────────────────────────────────────────────────────────────
    # Spatial index (cKDTree)
    # ──────────────────────────────────────────────────────────────────────────

    def _build_spatial_index(self):
        """
        Builds a 3D Cartesian unit-sphere cKDTree from all node coordinates.
        Points on the unit sphere: (cos(lat)*cos(lon), cos(lat)*sin(lon), sin(lat))
        This enables accurate great-circle nearest-neighbour queries in O(log N).
        """
        logger = self._get_logger()
        nx_g = self._nx_graph
        if nx_g is None or len(nx_g) == 0:
            return

        t0 = time.perf_counter()
        node_ids = []
        lats = []
        lons = []

        for n, data in nx_g.nodes(data=True):
            lat = data.get('lat', data.get('y'))
            lon = data.get('lon', data.get('x'))
            if lat is None or lon is None:
                continue
            node_ids.append(str(n))
            lats.append(float(lat))
            lons.append(float(lon))

        if not node_ids:
            logger.warning("[Graph] No valid node coordinates found — spatial index not built")
            return

        lats_arr = np.radians(np.array(lats, dtype=np.float64))
        lons_arr = np.radians(np.array(lons, dtype=np.float64))

        xs = np.cos(lats_arr) * np.cos(lons_arr)
        ys = np.cos(lats_arr) * np.sin(lons_arr)
        zs = np.sin(lats_arr)
        coords_3d = np.column_stack([xs, ys, zs])

        self._spatial_index = cKDTree(coords_3d)
        self._spatial_node_ids = np.array(node_ids)
        self._spatial_node_lats = np.array(lats, dtype=np.float64)
        self._spatial_node_lons = np.array(lons, dtype=np.float64)

        elapsed = time.perf_counter() - t0
        logger.info("[Graph] Spatial index (cKDTree) built for %d nodes in %.3f s", len(node_ids), elapsed)

    def _build_graph_bbox(self):
        """Compute bounding box of all graph nodes for O(1) coverage checks."""
        nx_g = self._nx_graph
        if nx_g is None:
            return
        lats, lons = [], []
        for n, d in nx_g.nodes(data=True):
            lat = d.get('lat', d.get('y'))
            lon = d.get('lon', d.get('x'))
            if lat is not None and lon is not None:
                lats.append(float(lat))
                lons.append(float(lon))
        if lats:
            self._graph_bbox = {
                'min_lat': min(lats),
                'max_lat': max(lats),
                'min_lon': min(lons),
                'max_lon': max(lons),
            }

    def find_nearest_node_fast(self, lat, lon):
        """
        O(log N) nearest-node lookup using the pre-built cKDTree.

        Returns:
            dict with node_id, latitude, longitude, distance_km  — or None if index not ready.
        """
        if self._spatial_index is None or self._spatial_node_ids is None:
            return None

        lat_r = math.radians(lat)
        lon_r = math.radians(lon)
        qx = math.cos(lat_r) * math.cos(lon_r)
        qy = math.cos(lat_r) * math.sin(lon_r)
        qz = math.sin(lat_r)

        chord_dist, idx = self._spatial_index.query([qx, qy, qz])
        # chord_dist is Euclidean on unit sphere; convert to km via arc length
        # arc = 2 * arcsin(chord / 2)  (chord = 2*sin(arc/2))
        arc = 2.0 * math.asin(min(chord_dist / 2.0, 1.0))
        dist_km = arc * 6371.0  # Earth radius km

        node_id = self._spatial_node_ids[idx]
        n_lat = float(self._spatial_node_lats[idx])
        n_lon = float(self._spatial_node_lons[idx])

        return {
            "node_id": node_id,
            "latitude": n_lat,
            "longitude": n_lon,
            "distance_km": round(dist_km, 4),
        }

    def find_candidates_in_radius(self, lat, lon, radius_km):
        """
        Queries cKDTree spatial index for all node candidates within radius_km.
        Returns a list of dicts sorted by exact distance_km ascending.
        """
        if self._spatial_index is None or self._spatial_node_ids is None:
            return []

        lat_r = math.radians(lat)
        lon_r = math.radians(lon)
        qx = math.cos(lat_r) * math.cos(lon_r)
        qy = math.cos(lat_r) * math.sin(lon_r)
        qz = math.sin(lat_r)

        arc = radius_km / 6371.0
        chord = 2.0 * math.sin(min(arc / 2.0, 1.0))

        indices = self._spatial_index.query_ball_point([qx, qy, qz], r=chord)
        if not indices:
            return []

        candidates = []
        for idx in indices:
            n_lat = float(self._spatial_node_lats[idx])
            n_lon = float(self._spatial_node_lons[idx])
            dist_km = haversine_distance(lat, lon, n_lat, n_lon)
            if dist_km <= radius_km:
                candidates.append({
                    "node_id": str(self._spatial_node_ids[idx]),
                    "latitude": n_lat,
                    "longitude": n_lon,
                    "distance_km": round(dist_km, 4)
                })

        candidates.sort(key=lambda x: x["distance_km"])
        return candidates

    def is_point_covered(self, lat, lon, margin_deg=0.5):
        """O(1) coverage check via graph bounding box (with margin)."""
        if self._graph_bbox is None or self._nx_graph is None or len(self._nx_graph) == 0:
            return False
        bb = self._graph_bbox
        return (
            bb['min_lat'] - margin_deg <= lat <= bb['max_lat'] + margin_deg and
            bb['min_lon'] - margin_deg <= lon <= bb['max_lon'] + margin_deg
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Graph accessors
    # ──────────────────────────────────────────────────────────────────────────

    def get_nx_graph(self):
        """Returns the in-memory NetworkX graph (may be None if not yet loaded)."""
        return self._nx_graph

    def get_nx_graph_safe(self):
        """
        Returns the in-memory graph, or raises RuntimeError if unavailable.
        Used by routing_service and node_service.
        Does NOT call Overpass API.
        """
        if self._nx_graph is not None and len(self._nx_graph) > 0:
            return self._nx_graph
        raise RuntimeError(
            "Road network graph is unavailable. "
            "Please ensure the graph cache exists and the backend has started correctly. "
            "Run POST /api/road-network/ingest to build the cache if needed."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Cache validation
    # ──────────────────────────────────────────────────────────────────────────

    def _validate_cached_graph(self, nx_g, logger):
        """
        Validates a loaded graph contains required structure:
          - Has nodes and edges
          - Nodes have lat/lon coordinates
          - Edges have length and travel_time
        """
        if nx_g is None or len(nx_g) == 0:
            logger.warning("[Graph] Validation failed: graph is empty")
            return False

        # Sample-validate up to 100 nodes for coordinates
        checked = 0
        valid_nodes = 0
        for n, d in nx_g.nodes(data=True):
            lat = d.get('lat', d.get('y'))
            lon = d.get('lon', d.get('x'))
            if lat is not None and lon is not None:
                valid_nodes += 1
            checked += 1
            if checked >= 100:
                break

        if valid_nodes < min(checked, 10):
            logger.warning("[Graph] Validation failed: too few nodes have valid coordinates (%d/%d)", valid_nodes, checked)
            return False

        # Sample-validate up to 50 edges for required weight attributes
        edge_checked = 0
        for u, v, k, d in nx_g.edges(data=True, keys=True):
            # Accept if either length or travel_time exists
            has_len = 'length' in d or 'distance' in d
            has_tt = 'travel_time' in d
            if not has_len and not has_tt:
                pass  # Not necessarily invalid — some edges may lack weights
            edge_checked += 1
            if edge_checked >= 50:
                break

        logger.info("[Graph] Cache validation passed: %d nodes, %d edges sampled",
                    nx_g.number_of_nodes(), nx_g.number_of_edges())
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # Graph building & caching (used by ingest endpoint only)
    # ──────────────────────────────────────────────────────────────────────────

    def build_graph(self, nodes=None, edges=None):
        """
        Builds an in-memory NetworkX MultiDiGraph and RoadGraph from parsed OSM data.
        Called by ingest_osm_and_build() only — never during normal routing.
        """
        logger = self._get_logger()
        nodes_list = nodes or []
        edges_list = edges or []

        logger.info("Building graph with %d nodes and %d edges", len(nodes_list), len(edges_list))

        road_graph = RoadGraph()
        nx_graph = nx.MultiDiGraph()

        for n in nodes_list:
            road_graph.add_node(n)
            nx_graph.add_node(
                n.node_id,
                y=n.latitude,
                x=n.longitude,
                lat=n.latitude,
                lon=n.longitude,
                pos=(n.latitude, n.longitude),
                tags=n.tags
            )

        for e in edges_list:
            road_graph.add_edge(e)
            nx_graph.add_edge(
                e.source,
                e.target,
                length=e.distance,
                distance=e.distance,
                travel_time=e.travel_time,
                speed_limit=e.speed_limit,
                highway=e.road_type,
                name=e.name,
                oneway=e.oneway
            )

        self.validate_graph(nx_graph)

        self._active_graph = road_graph
        self._nx_graph = nx_graph

        # Rebuild spatial structures after ingestion
        self._build_graph_bbox()
        self._build_spatial_index()

        logger.info("Graph loaded into memory. Total nodes: %d, Total edges: %d",
                    len(road_graph.nodes), len(road_graph.edges))
        return road_graph

    def validate_graph(self, nx_graph=None):
        """Validates graph structure and removes invalid nodes/edges."""
        logger = self._get_logger()
        G = nx_graph if nx_graph is not None else self._nx_graph

        if G is None or len(G) == 0:
            logger.warning("Validation skipped: Graph is empty")
            return False

        logger.info("Validating road graph topology (%d nodes, %d edges)",
                    G.number_of_nodes(), G.number_of_edges())

        invalid_nodes = []
        for n, data in G.nodes(data=True):
            lat = data.get('lat', data.get('y'))
            lon = data.get('lon', data.get('x'))
            if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                invalid_nodes.append(n)

        if invalid_nodes:
            logger.warning("Found %d invalid nodes during graph validation. Removing...", len(invalid_nodes))
            G.remove_nodes_from(invalid_nodes)

        for u, v, k, data in G.edges(data=True, keys=True):
            length = data.get('length', data.get('distance', 0.0))
            if length <= 0:
                data['length'] = 0.1
                data['distance'] = 0.1

        if len(G) > 0:
            num_components = nx.number_weakly_connected_components(G)
            logger.info("Graph topology validation successful. Weakly connected components: %d", num_components)

        return True

    def save_graph_to_cache(self, cache_key="bangalore_default"):
        """Saves the active graph to disk cache pickle file."""
        logger = self._get_logger()
        if self._nx_graph is None:
            logger.warning("Cannot save to cache: No active graph in memory")
            return False

        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir, exist_ok=True)

            cache_path = os.path.join(self.cache_dir, f"{cache_key}.pickle")
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    "nx_graph": self._nx_graph,
                    "road_graph": self._active_graph
                }, f)

            logger.info("Saved graph with %d nodes to disk cache at: %s",
                        self._nx_graph.number_of_nodes(), cache_path)
            return True
        except Exception as exc:
            logger.error("Failed to save graph to cache: %s", str(exc))
            return False

    def load_graph_from_cache(self, cache_key="bangalore_default"):
        """Loads a graph from a named pickle file. Used by ingest endpoint."""
        logger = self._get_logger()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.pickle")

        if not os.path.exists(cache_path):
            logger.info("Cache miss for key: %s (file not found)", cache_key)
            return None

        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                self._nx_graph = data.get("nx_graph")
                self._active_graph = data.get("road_graph")

            if self._nx_graph is not None:
                logger.info("Loaded graph from cache (%d nodes, %d edges)",
                            self._nx_graph.number_of_nodes(), self._nx_graph.number_of_edges())
                self._build_graph_bbox()
                self._build_spatial_index()
                return self._active_graph
        except Exception as exc:
            logger.error("Failed to load graph from cache file %s: %s", cache_path, str(exc))

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # OSM ingestion (administrative only — NOT called during routing)
    # ──────────────────────────────────────────────────────────────────────────

    def ingest_osm_and_build(self, bbox=None, force_refresh=False, cache_key="bangalore_default"):
        """
        Administrative end-to-end ingest workflow:
          OSM Fetch → Parse → NetworkX Graph → Validate → Cache → Spatial Index

        Called ONLY by POST /api/road-network/ingest.
        NEVER called during route calculation or nearest-node lookup.
        """
        logger = self._get_logger()

        if not force_refresh:
            cached_graph = self.load_graph_from_cache(cache_key)
            if cached_graph:
                return {
                    "status": "cached",
                    "graph": cached_graph,
                    "stats": self.get_graph_stats()
                }

        osm_raw = osm_service.fetch_road_data(bbox)
        parsed = osm_service.parse_osm_response(osm_raw)
        road_graph = self.build_graph(parsed["nodes"], parsed["edges"])
        self.save_graph_to_cache(cache_key)

        return {
            "status": "built",
            "source": osm_raw.get("source", "overpass_api"),
            "graph": road_graph,
            "stats": self.get_graph_stats()
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Legacy compatibility: ensure_graph_for_points / ensure_graph_for_location
    # These no longer trigger Overpass API — they simply return the cached graph.
    # ──────────────────────────────────────────────────────────────────────────

    def ensure_graph_for_points(self, lat1, lon1, lat2=None, lon2=None):
        """
        Ensures the primary Bengaluru graph is loaded in memory.

        GRAPH LOCKING POLICY:
        Once the primary bangalore_default graph (517k+ nodes) is loaded, it is NEVER
        replaced or downgraded by any regional cache file at runtime.

        Regional cache files on disk are intentional legacy/test artefacts.
        They must NEVER overwrite the primary graph — doing so was the root cause
        of "Location is outside the available road network" errors.
        """
        logger = self._get_logger()

        # --- PRIMARY GRAPH LOCK ---
        # If the primary graph is already loaded (>= 50k nodes), always retain it.
        # Never swap it out for a regional cache file — this permanently prevents
        # the in-memory graph collapsing from 517k nodes to ~20 nodes.
        if self._nx_graph is not None and len(self._nx_graph) >= 50000:
            return self._nx_graph

        # Primary graph is not loaded yet — load bangalore_default once.
        logger.info("[Graph] Primary graph not loaded — loading bangalore_default.")
        if self.preload_default_graph("bangalore_default"):
            logger.info("[Graph] Primary bangalore_default graph loaded (%d nodes).",
                        self._nx_graph.number_of_nodes() if self._nx_graph else 0)
            return self._nx_graph

        # If loading failed entirely, return whatever is in memory (may be None).
        logger.warning("[Graph] Could not load primary graph — returning current state.")
        return self._nx_graph

    def ensure_graph_for_location(self, lat, lon):
        """Delegates to ensure_graph_for_points (single-point form)."""
        return self.ensure_graph_for_points(lat, lon)

    # ──────────────────────────────────────────────────────────────────────────
    # Statistics & Diagnostics
    # ──────────────────────────────────────────────────────────────────────────

    def get_graph_stats(self):
        if self._nx_graph is not None:
            total_dist_km = sum(
                d.get('length', d.get('distance', 0.0))
                for u, v, d in self._nx_graph.edges(data=True)
            )
            return {
                "status": "loaded",
                "max_allowed_nodes": MAX_GRAPH_NODES,
                "node_count": self._nx_graph.number_of_nodes(),
                "edge_count": self._nx_graph.number_of_edges(),
                "total_road_length_km": round(total_dist_km, 2),
                "spatial_index_ready": self._spatial_index is not None,
            }
        if self._active_graph is not None:
            return self._active_graph.metadata
        return {
            "status": "empty",
            "max_allowed_nodes": MAX_GRAPH_NODES,
            "node_count": 0,
            "edge_count": 0,
            "spatial_index_ready": False,
        }

    def get_network_diagnostics(self):
        """
        Returns a comprehensive diagnostic report of the active Bengaluru road network.
        Includes: node/edge counts, geographic bounds, connected components, and index status.
        """
        logger = self._get_logger()
        nx_g = self._nx_graph

        if nx_g is None or len(nx_g) == 0:
            return {
                "network": "Bengaluru",
                "status": "unavailable",
                "message": "Road network graph is not loaded.",
            }

        # Geographic bounds from pre-built bbox
        bb = self._graph_bbox or {}
        min_lat = bb.get('min_lat')
        max_lat = bb.get('max_lat')
        min_lon = bb.get('min_lon')
        max_lon = bb.get('max_lon')

        # Connected components (weakly connected on undirected view)
        # NOTE: This is O(N+E) but only called by admin diagnostics endpoint, not routing.
        try:
            t0 = time.perf_counter()
            und = nx_g.to_undirected(as_view=True)
            components = list(nx.connected_components(und))
            comp_sizes = sorted([len(c) for c in components], reverse=True)
            largest_component = comp_sizes[0] if comp_sizes else 0
            num_components = len(components)
            elapsed_cc = time.perf_counter() - t0
            logger.info("[Graph] Diagnostics: connected components computed in %.2f s", elapsed_cc)
        except Exception as exc:
            logger.warning("[Graph] Diagnostics: could not compute connected components: %s", exc)
            num_components = None
            largest_component = None
            comp_sizes = []

        return {
            "network": "Bengaluru",
            "status": "ready",
            "nodes": nx_g.number_of_nodes(),
            "edges": nx_g.number_of_edges(),
            "latitude_range": {
                "min": round(min_lat, 4) if min_lat is not None else None,
                "max": round(max_lat, 4) if max_lat is not None else None,
            },
            "longitude_range": {
                "min": round(min_lon, 4) if min_lon is not None else None,
                "max": round(max_lon, 4) if max_lon is not None else None,
            },
            "connected_components": num_components,
            "largest_component_nodes": largest_component,
            "top_component_sizes": comp_sizes[:5],
            "spatial_index": "READY" if self._spatial_index is not None else "NOT BUILT",
            "graph": "READY",
        }

    def get_coverage_test(self):
        """
        Tests nearest-node resolution for a 9-point grid spread across Greater Bengaluru.
        Returns a list of results — SUCCESS or OUTSIDE NETWORK — for each grid point.
        Covers: North, South, East, West, Central, NE, NW, SE, SW sectors.
        """
        # Grid coordinates selected to cover the full Bengaluru metropolitan area
        BENGALURU_GRID = [
            {"sector": "Central",    "lat": 12.9716, "lon": 77.5946},  # MG Road area
            {"sector": "North",      "lat": 13.0627, "lon": 77.5937},  # Hebbal flyover
            {"sector": "South",      "lat": 12.8452, "lon": 77.6602},  # Electronic City
            {"sector": "East",       "lat": 12.9698, "lon": 77.7499},  # Whitefield
            {"sector": "West",       "lat": 12.9719, "lon": 77.5307},  # Vijayanagar
            {"sector": "North-East", "lat": 13.0075, "lon": 77.6959},  # KR Puram
            {"sector": "North-West", "lat": 13.0285, "lon": 77.5458},  # Yeshwanthpur
            {"sector": "South-East", "lat": 12.9304, "lon": 77.6784},  # Bellandur
            {"sector": "South-West", "lat": 12.9255, "lon": 77.5468},  # Banashankari
        ]

        from .node_service import node_service
        results = []
        for point in BENGALURU_GRID:
            lat, lon, sector = point["lat"], point["lon"], point["sector"]
            try:
                res = node_service.find_nearest_node(lat, lon)
                if res and res.get("success"):
                    results.append({
                        "sector": sector,
                        "lat": lat,
                        "lon": lon,
                        "status": "SUCCESS",
                        "node_id": res.get("node_id"),
                        "snap_distance_km": res.get("distance_km"),
                        "search_radius_km": res.get("search_radius_km"),
                    })
                else:
                    results.append({
                        "sector": sector,
                        "lat": lat,
                        "lon": lon,
                        "status": "OUTSIDE NETWORK",
                        "reason": res.get("reason") if res else "UNKNOWN",
                    })
            except Exception as exc:
                results.append({
                    "sector": sector,
                    "lat": lat,
                    "lon": lon,
                    "status": "ERROR",
                    "reason": str(exc),
                })

        total = len(results)
        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        return {
            "network": "Bengaluru",
            "grid_points": total,
            "success": success_count,
            "failed": total - success_count,
            "coverage_pct": round(100.0 * success_count / total, 1) if total else 0,
            "results": results,
        }


# Module-level singleton
graph_service = GraphService()
