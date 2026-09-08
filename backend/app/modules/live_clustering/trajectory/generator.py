"""
Road-Constrained Bengaluru Vehicle Trajectory Generator

NOTE: This module produces SYNTHETIC validation trajectories to evaluate the DBSCAN
vehicle clustering algorithm against ground-truth carpool/multi-user data. It is NOT a
live user GPS feed and must NOT be presented as a live data source.
"""
import math
import random
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
import networkx as nx

from app.modules.road_network.services.graph_service import graph_service
from app.modules.road_network.utils.geo_utils import haversine_distance
from app.modules.live_clustering.spatial_filter import haversine_distance_meters
from ..config import GPS_NOISE_METERS, USER_POSITION_JITTER_METERS
from .schemas import Observation, GroundTruthVehicle, TrajectoryDataset

logger = logging.getLogger("routeflow.live_clustering.trajectory.generator")


def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates bearing from point 1 to point 2 in degrees (0 to 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lam = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lam)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def _add_gps_noise(lat: float, lon: float, noise_meters: float) -> Tuple[float, float]:
    """Applies random radial GPS noise in meters."""
    if noise_meters <= 0:
        return lat, lon
    
    dlat = (random.gauss(0, noise_meters / 2.0)) / 111320.0
    dlon = (random.gauss(0, noise_meters / 2.0)) / (111320.0 * math.cos(math.radians(lat)))
    return round(lat + dlat, 6), round(lon + dlon, 6)


class TrajectoryGenerator:
    """
    Generates synthetic road-constrained vehicle trajectories inside a given area.
    
    Key Features:
      - Uses existing NetworkX graph in READ-ONLY mode.
      - Trajectories follow actual road edge geometry.
      - Supports multiple users per vehicle (e.g. carpoolers / passengers).
      - Multi-user observations feature configurable GPS noise and jitter.
      - Exposes ground truth vehicle metadata separately for evaluation.
    """
    
    def generate_area_trajectories(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float = 1000.0,
        area_name: str = "Selected Area",
        num_vehicles: int = 15,
        multi_user_ratio: float = 0.5, # 50% of vehicles carry multiple users
        duration_minutes: float = 5.0,
        time_step_seconds: float = 2.0,
        seed: Optional[int] = 42,
    ) -> Tuple[TrajectoryDataset, Dict[str, str]]:
        """
        Generates road-constrained vehicle trajectories strictly inside the selected area radius.
        """
        if seed is not None:
            random.seed(seed)
            
        radius_km = radius_meters / 1000.0
        
        # Stage 1 candidate lookup
        candidates = graph_service.find_candidates_in_radius(center_lat, center_lon, radius_km * 1.2)
        if not candidates:
            fast_node = graph_service.find_nearest_node_fast(center_lat, center_lon)
            if fast_node:
                candidates = [fast_node]
                
        node_ids = [c["node_id"] for c in candidates] if candidates else []
        nx_g = graph_service.get_nx_graph()

        # Stage 2 exact distance screening on candidates
        valid_nodes = []
        if nx_g is not None:
            for n in node_ids:
                if nx_g.has_node(n):
                    n_d = nx_g.nodes[n]
                    n_lat = n_d.get("lat", n_d.get("y"))
                    n_lon = n_d.get("lon", n_d.get("x"))
                    if n_lat and n_lon:
                        if haversine_distance_meters(center_lat, center_lon, float(n_lat), float(n_lon)) <= radius_meters:
                            valid_nodes.append(n)
        
        if nx_g is None or len(valid_nodes) < 2:
            logger.info("[TrajectoryGenerator] Creating synthetic local road network for %s within %.1fm", area_name, radius_meters)
            nx_g = nx.DiGraph()
            valid_nodes = []
            grid_span_deg = (radius_meters / 111320.0) * 0.7
            for r in range(4):
                for c in range(4):
                    nid = r * 4 + c + 10000
                    lat_val = center_lat + (r - 1.5) * (grid_span_deg / 2.0)
                    lon_val = center_lon + (c - 1.5) * (grid_span_deg / 2.0)
                    if haversine_distance_meters(center_lat, center_lon, lat_val, lon_val) <= radius_meters:
                        nx_g.add_node(nid, lat=lat_val, lon=lon_val)
                        valid_nodes.append(nid)
            for r in range(4):
                for c in range(4):
                    u = r * 4 + c + 10000
                    if u in valid_nodes:
                        if c < 3:
                            v = u + 1
                            if v in valid_nodes:
                                nx_g.add_edge(u, v, length=200.0, name="Bengaluru Local Road")
                                nx_g.add_edge(v, u, length=200.0, name="Bengaluru Local Road")
                        if r < 3:
                            v = u + 4
                            if v in valid_nodes:
                                nx_g.add_edge(u, v, length=200.0, name="Bengaluru Local Road")
                                nx_g.add_edge(v, u, length=200.0, name="Bengaluru Local Road")
        
        if not valid_nodes:
            # Fallback node exactly at center
            center_nid = 99999
            nx_g.add_node(center_nid, lat=center_lat, lon=center_lon)
            valid_nodes = [center_nid]

        gt_vehicles: List[GroundTruthVehicle] = []
        user_to_vehicle_map: Dict[str, str] = {}
        all_observations: List[Observation] = []
        
        start_time = datetime.now(timezone.utc)
        num_steps = int((duration_minutes * 60.0) / time_step_seconds)
        
        user_counter = 1
        
        for v_idx in range(1, num_vehicles + 1):
            vehicle_id = f"veh_{v_idx:03d}"
            
            # Decide users for this vehicle
            if random.random() < multi_user_ratio:
                users_in_veh_count = random.randint(2, 4)
            else:
                users_in_veh_count = 1
                
            veh_user_ids = []
            for _ in range(users_in_veh_count):
                u_id = f"user_{user_counter:03d}"
                user_counter += 1
                veh_user_ids.append(u_id)
                user_to_vehicle_map[u_id] = vehicle_id
                
            start_n = random.choice(valid_nodes)
            end_n = random.choice(valid_nodes)
            
            path = None
            try:
                if nx.has_path(nx_g, start_n, end_n):
                    path = nx.shortest_path(nx_g, start_n, end_n, weight="length")
            except Exception:
                path = None
                
            if not path or len(path) < 2:
                path = [start_n, end_n]
                
            gt_vehicles.append(GroundTruthVehicle(
                vehicle_id=vehicle_id,
                user_ids=veh_user_ids,
                start_node=str(start_n),
                end_node=str(end_n),
                path_nodes=[str(p) for p in path],
                base_speed_kmh=round(random.uniform(25.0, 55.0), 1)
            ))
            
            path_coords = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                u_d = nx_g.nodes.get(u, {})
                v_d = nx_g.nodes.get(v, {})
                u_lat, u_lon = u_d.get("lat", u_d.get("y")), u_d.get("lon", u_d.get("x"))
                v_lat, v_lon = v_d.get("lat", v_d.get("y")), v_d.get("lon", v_d.get("x"))
                if u_lat and u_lon and v_lat and v_lon:
                    path_coords.append((float(u_lat), float(u_lon), float(v_lat), float(v_lon), f"{u}_{v}"))
                    
            if not path_coords:
                c_d = nx_g.nodes.get(start_n, {})
                c_lat = c_d.get("lat", center_lat)
                c_lon = c_d.get("lon", center_lon)
                path_coords.append((c_lat, c_lon, c_lat + 0.0005, c_lon + 0.0005, f"{start_n}_{end_n}"))
                
            total_edges = len(path_coords)
            base_speed = gt_vehicles[-1].base_speed_kmh
            
            for step in range(num_steps):
                step_time = start_time + timedelta(seconds=step * time_step_seconds)
                timestamp_iso = step_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                edge_idx = (step // max(1, num_steps // total_edges)) % total_edges
                u_lat, u_lon, v_lat, v_lon, edge_id = path_coords[edge_idx]
                
                steps_per_edge = max(1, num_steps // total_edges)
                t = (step % steps_per_edge) / float(steps_per_edge)
                
                veh_lat = u_lat + t * (v_lat - u_lat)
                veh_lon = u_lon + t * (v_lon - u_lon)
                heading = _calculate_bearing(u_lat, u_lon, v_lat, v_lon)
                
                # Check vehicle location distance
                if haversine_distance_meters(center_lat, center_lon, veh_lat, veh_lon) > radius_meters:
                    continue

                for u_id in veh_user_ids:
                    u_lat_noisy, u_lon_noisy = _add_gps_noise(
                        veh_lat, veh_lon, GPS_NOISE_METERS + random.uniform(0, USER_POSITION_JITTER_METERS)
                    )
                    
                    # STAGE 2 Observation Check (Requirement 7)
                    if haversine_distance_meters(center_lat, center_lon, u_lat_noisy, u_lon_noisy) > radius_meters:
                        continue

                    user_speed = round(max(5.0, base_speed + random.uniform(-3.0, 3.0)), 1)
                    user_heading = round((heading + random.uniform(-4.0, 4.0)) % 360.0, 1)
                    
                    obs = Observation(
                        observation_id=f"obs_{uuid.uuid4().hex[:10]}",
                        user_id=u_id,
                        timestamp=timestamp_iso,
                        latitude=u_lat_noisy,
                        longitude=u_lon_noisy,
                        speed_kmh=user_speed,
                        heading=user_heading,
                        accuracy_m=round(random.uniform(3.0, 8.0), 1),
                        road_edge_id=edge_id,
                    )
                    all_observations.append(obs)

                    
        # Sort all observations chronologically
        all_observations.sort(key=lambda x: x.timestamp)
        
        dataset = TrajectoryDataset(
            dataset_id=f"ds_{uuid.uuid4().hex[:8]}",
            area_name=area_name,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_meters=radius_meters,
            vehicle_count=len(gt_vehicles),
            user_count=len(user_to_vehicle_map),
            total_observations=len(all_observations),
            vehicles=gt_vehicles,
            observations=all_observations,
        )
        
        logger.info(
            "[TrajectoryGenerator] Generated dataset '%s' for area '%s': %d vehicles, %d users, %d observations",
            dataset.dataset_id, area_name, dataset.vehicle_count, dataset.user_count, dataset.total_observations
        )
        return dataset, user_to_vehicle_map


generator = TrajectoryGenerator()
trajectory_generator = generator
