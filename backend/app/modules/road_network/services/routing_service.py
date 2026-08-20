import logging
import networkx as nx
from flask import current_app
from ..services.graph_service import graph_service
from ..services.node_service import node_service
from ..utils.geo_utils import haversine_distance, calculate_travel_time

def _haversine_heuristic(u, v, nx_graph):
    """
    Heuristic function for A* search: calculates Haversine distance in km
    between nodes u and v using node spatial attributes.
    """
    try:
        u_data = nx_graph.nodes[u]
        v_data = nx_graph.nodes[v]
        u_lat = u_data.get('lat', u_data.get('y'))
        u_lon = u_data.get('lon', u_data.get('x'))
        v_lat = v_data.get('lat', v_data.get('y'))
        v_lon = v_data.get('lon', v_data.get('x'))

        if u_lat is not None and u_lon is not None and v_lat is not None and v_lon is not None:
            # Distance in km
            return haversine_distance(u_lat, u_lon, v_lat, v_lon)
    except Exception:
        pass
    return 0.0

class RoutingService:
    """
    Service responsible for calculating optimal paths using Dijkstra and A* algorithms
    over the NetworkX Road Network Graph.
    """
    def _get_logger(self):
        try:
            if current_app and hasattr(current_app, 'logger') and current_app.logger:
                return current_app.logger
        except Exception:
            pass
        return logging.getLogger("routeflow.road_network.routing")

    def calculate_route(self, source_node_id, target_node_id, algorithm="astar", weight="travel_time"):
        """
        Calculates the optimal route between source_node_id and target_node_id using A* or Dijkstra algorithm.

        :param source_node_id: ID of the starting graph node
        :param target_node_id: ID of the destination graph node
        :param algorithm: 'astar' or 'dijkstra'
        :param weight: 'travel_time' (seconds) or 'distance' (km)
        :returns: dict with path geometry, distance, duration, and segment details
        """
        logger = self._get_logger()
        logger.info("Routing requested: %s -> %s using %s (weight: %s)", source_node_id, target_node_id, algorithm, weight)

        nx_graph = graph_service.get_nx_graph()
        if nx_graph is None or len(nx_graph) == 0:
            # Try to auto-load cached graph if not active in memory
            graph_service.ingest_osm_and_build()
            nx_graph = graph_service.get_nx_graph()

        if nx_graph is None or len(nx_graph) == 0:
            raise ValueError("Road network graph is not available. Please ingest road data first.")

        src = str(source_node_id)
        tgt = str(target_node_id)

        if src not in nx_graph:
            raise ValueError(f"Source node '{src}' is not present in the routing graph.")
        if tgt not in nx_graph:
            raise ValueError(f"Destination node '{tgt}' is not present in the routing graph.")

        if src == tgt:
            node_data = nx_graph.nodes[src]
            lat = node_data.get('lat', node_data.get('y'))
            lon = node_data.get('lon', node_data.get('x'))
            return {
                "algorithm": algorithm,
                "weight_criterion": weight,
                "source_node_id": src,
                "target_node_id": tgt,
                "total_distance_km": 0.0,
                "total_duration_minutes": 0.0,
                "total_duration_seconds": 0.0,
                "node_count": 1,
                "path_nodes": [src],
                "geometry": [[lat, lon]] if lat and lon else [],
                "segments": []
            }

        # Weight attribute mapping
        weight_attr = 'travel_time' if weight == 'travel_time' else 'length'

        try:
            if algorithm.lower() == 'dijkstra':
                path_nodes = nx.dijkstra_path(
                    nx_graph,
                    src,
                    tgt,
                    weight=weight_attr
                )
            else:
                # Default to A* Search
                algorithm = 'astar'
                heuristic_fn = lambda u, v: _haversine_heuristic(u, v, nx_graph)
                path_nodes = nx.astar_path(
                    nx_graph,
                    src,
                    tgt,
                    heuristic=heuristic_fn,
                    weight=weight_attr
                )
        except nx.NetworkXNoPath:
            logger.warning("No path exists between node %s and node %s", src, tgt)
            raise ValueError(f"No valid road path exists between source node '{src}' and destination node '{tgt}'.")
        except Exception as e:
            logger.error("Pathfinding error (%s): %s", algorithm, str(e))
            raise ValueError(f"Route calculation failed: {str(e)}")

        # Construct path geometry, distance, and duration metrics
        geometry = []
        segments = []
        total_dist_km = 0.0
        total_time_sec = 0.0

        for i in range(len(path_nodes)):
            curr_id = path_nodes[i]
            curr_data = nx_graph.nodes[curr_id]
            lat = curr_data.get('lat', curr_data.get('y'))
            lon = curr_data.get('lon', curr_data.get('x'))

            if lat is not None and lon is not None:
                geometry.append([float(lat), float(lon)])

            if i < len(path_nodes) - 1:
                next_id = path_nodes[i + 1]
                # Extract edge data (select edge with lowest travel_time if MultiDiGraph)
                edge_data_map = nx_graph.get_edge_data(curr_id, next_id) or {}
                best_edge = {}
                best_tt = float("inf")
                if isinstance(edge_data_map, dict):
                    for k, ed in edge_data_map.items():
                        tt = float(ed.get('travel_time', ed.get('length', 0.0)) or 0.0)
                        if tt < best_tt:
                            best_tt = tt
                            best_edge = ed

                dist_km = float(best_edge.get('length', best_edge.get('distance', 0.0)) or 0.0)
                time_sec = float(best_edge.get('travel_time', 0.0) or 0.0)
                road_name = best_edge.get('name', 'Road')
                highway = best_edge.get('highway', 'default')

                total_dist_km += dist_km
                total_time_sec += time_sec

                segments.append({
                    "from_node": curr_id,
                    "to_node": next_id,
                    "distance_km": round(dist_km, 4),
                    "travel_time_sec": round(time_sec, 2),
                    "road_name": road_name,
                    "road_type": highway
                })

        total_duration_min = round(total_time_sec / 60.0, 2)
        total_dist_km = round(total_dist_km, 3)

        logger.info("Route calculated successfully: %d nodes, %.2f km, %.2f mins", len(path_nodes), total_dist_km, total_duration_min)

        return {
            "algorithm": algorithm,
            "weight_criterion": weight,
            "source_node_id": src,
            "target_node_id": tgt,
            "total_distance_km": total_dist_km,
            "total_duration_minutes": total_duration_min,
            "total_duration_seconds": round(total_time_sec, 1),
            "node_count": len(path_nodes),
            "segment_count": len(segments),
            "path_nodes": path_nodes,
            "geometry": geometry,
            "segments": segments
        }

    def calculate_route_from_coords(self, source_lat, source_lon, target_lat, target_lon, algorithm="dijkstra", weight="travel_time"):
        """
        Convenience method: resolves nearest nodes for coordinates first, then calculates route.
        Ensures a single regional graph covering both source and target is loaded.
        """
        graph_service.ensure_graph_for_points(source_lat, source_lon, target_lat, target_lon)

        src_node = node_service.find_nearest_node(source_lat, source_lon)
        tgt_node = node_service.find_nearest_node(target_lat, target_lon)

        if not src_node or not src_node.get("success", True):
            raise ValueError(f"Source location ({source_lat}, {source_lon}) is outside supported road network coverage.")
        if not tgt_node or not tgt_node.get("success", True):
            raise ValueError(f"Destination location ({target_lat}, {target_lon}) is outside supported road network coverage.")

        res = self.calculate_route(
            source_node_id=src_node["node_id"],
            target_node_id=tgt_node["node_id"],
            algorithm=algorithm,
            weight=weight
        )
        res["source_snap_distance_km"] = src_node.get("distance_km", 0.0)
        res["target_snap_distance_km"] = tgt_node.get("distance_km", 0.0)
        return res

routing_service = RoutingService()
