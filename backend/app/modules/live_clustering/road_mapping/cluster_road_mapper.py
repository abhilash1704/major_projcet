"""
Road-Level Vehicle Density Mapper
"""
import logging
from typing import Dict, Any, List
from app.modules.road_network.services.graph_service import graph_service
from ..config import LOW_DENSITY_MAX, HIGH_DENSITY_MIN

logger = logging.getLogger("routeflow.live_clustering.road_mapping.cluster_road_mapper")


class ClusterRoadMapper:
    """
    Maps estimated vehicle clusters onto RouteFlow road edges and computes edge density.
    """
    
    def compute_road_density(
        self,
        clusters: List[Dict[str, Any]],
        center_lat: float,
        center_lon: float
    ) -> Dict[str, Any]:
        """
        Maps clusters to road edges and returns road density breakdown.
        """
        if not clusters:
            return {
                "status": "INACTIVE",
                "total_active_edges": 0,
                "high_density_count": 0,
                "medium_density_count": 0,
                "low_density_count": 0,
                "road_segments": [],
            }

        edge_cluster_map: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Group clusters by primary road edge
        for clus in clusters:
            edge_id = clus.get("primary_road_edge_id")
            if not edge_id:
                # Nearest edge lookup fallback
                c_lat = clus.get("center_latitude")
                c_lon = clus.get("center_longitude")
                if c_lat and c_lon:
                    node = graph_service.find_nearest_node_fast(c_lat, c_lon)
                    if node:
                        edge_id = f"{node['node_id']}_nearest"

            if edge_id:
                if edge_id not in edge_cluster_map:
                    edge_cluster_map[edge_id] = []
                edge_cluster_map[edge_id].append(clus)

        # 2. Build road density breakdown per edge
        nx_g = graph_service.ensure_graph_for_points(center_lat, center_lon)
        road_segments = []

        high_cnt, med_cnt, low_cnt = 0, 0, 0

        for edge_id, clus_list in edge_cluster_map.items():
            vehicle_count = len(clus_list)
            
            if vehicle_count <= LOW_DENSITY_MAX:
                density_level = "LOW"
                color = "#22c55e"  # Green
                low_cnt += 1
            elif vehicle_count < HIGH_DENSITY_MIN:
                density_level = "MEDIUM"
                color = "#f59e0b"  # Orange
                med_cnt += 1
            else:
                density_level = "HIGH"
                color = "#ef4444"  # Red
                high_cnt += 1

            # Resolve geometry from graph if standard edge format u_v
            geometry = None
            edge_name = "Bengaluru Road Segment"
            
            parts = edge_id.split("_")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit() and nx_g:
                u, v = int(parts[0]), int(parts[1])
                if nx_g.has_edge(u, v):
                    data = nx_g.get_edge_data(u, v)
                    edge_name = data.get("name", edge_name) if isinstance(data, dict) else edge_name
                    u_d = nx_g.nodes.get(u, {})
                    v_d = nx_g.nodes.get(v, {})
                    u_lat, u_lon = u_d.get("lat", u_d.get("y")), u_d.get("lon", u_d.get("x"))
                    v_lat, v_lon = v_d.get("lat", v_d.get("y")), v_d.get("lon", v_d.get("x"))
                    if u_lat and u_lon and v_lat and v_lon:
                        geometry = [[float(u_lat), float(u_lon)], [float(v_lat), float(v_lon)]]

            if not geometry and clus_list:
                # Fallback geometry around cluster center
                c_lat = clus_list[0]["center_latitude"]
                c_lon = clus_list[0]["center_longitude"]
                geometry = [[c_lat - 0.0005, c_lon - 0.0005], [c_lat + 0.0005, c_lon + 0.0005]]

            road_segments.append({
                "road_edge_id": edge_id,
                "road_name": edge_name,
                "estimated_vehicle_count": vehicle_count,
                "vehicle_count": vehicle_count,
                "density_level": density_level,
                "density_rank": density_level,
                "color": color,
                "cluster_ids": [c["cluster_id"] for c in clus_list],
                "geometry": geometry,
            })

        return {
            "status": "ACTIVE",
            "total_active_edges": len(road_segments),
            "high_density_count": high_cnt,
            "medium_density_count": med_cnt,
            "low_density_count": low_cnt,
            "road_segments": road_segments,
        }


cluster_road_mapper = ClusterRoadMapper()
