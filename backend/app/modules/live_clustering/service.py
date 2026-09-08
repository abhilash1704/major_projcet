"""
Live Clustering — Service Orchestrator
"""
import logging
from typing import Dict, Any, Optional

from .area.area_service import get_all_areas, get_area_by_id
from .traffic.traffic_provider_service import get_area_traffic
from .traffic.traffic_normalizer import map_traffic_payload
from .trajectory.generator import generator
from .trajectory.replay_engine import replay_engine
from .trajectory.trajectory_store import trajectory_store
from .clustering.vehicle_cluster_service import vehicle_cluster_service
from .road_mapping.cluster_road_mapper import cluster_road_mapper
from .evaluation.clustering_metrics import evaluation_engine

logger = logging.getLogger("routeflow.live_clustering.service")


import uuid
import time
import logging
from typing import Dict, Any, Optional

from .area.area_service import get_all_areas, get_area_by_id
from .traffic.traffic_provider_service import get_area_traffic
from .traffic.traffic_normalizer import map_traffic_payload
from .trajectory.generator import generator
from .trajectory.replay_engine import replay_engine
from .trajectory.trajectory_store import trajectory_store
from .clustering.vehicle_cluster_service import vehicle_cluster_service
from .road_mapping.cluster_road_mapper import cluster_road_mapper
from .evaluation.clustering_metrics import evaluation_engine

logger = logging.getLogger("routeflow.live_clustering.service")


class LiveClusteringService:
    """
    Main service facade for the Live Clustering module with automatic 20s cycle support.
    """
    
    def __init__(self):
        self._current_area: Dict[str, Any] = {
            "id": "silk_board",
            "name": "Silk Board Junction",
            "latitude": 12.9174,
            "longitude": 77.6228,
            "radius_meters": 1000.0,
            "source": "preset",
        }
        self._session_id: str = str(uuid.uuid4())
        self._generation_counter: int = 0
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._last_update_timestamp: float = time.time()

    def set_active_area(
        self,
        lat: float,
        lon: float,
        name: str = "Selected Area",
        area_id: Optional[str] = None,
        radius_m: float = 1000.0,
        source: str = "preset"
    ) -> Dict[str, Any]:
        new_id = area_id or f"custom_{round(lat,4)}_{round(lon,4)}"
        
        # Reset session and clear stores if area or radius changed (Requirement 13 & 14)
        if (self._current_area.get("id") != new_id or 
            abs(self._current_area.get("radius_meters", 1000.0) - radius_m) > 1.0):
            self._session_id = str(uuid.uuid4())
            self._generation_counter = 0
            self._last_snapshot = None
            try:
                trajectory_store.clear()
                replay_engine.stop()
            except Exception as err:
                logger.warning("Error clearing replay store on area change: %s", err)

        self._current_area = {
            "id": new_id,
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "radius_meters": radius_m,
            "source": source,
        }
        return self.get_active_area()

    def get_active_area(self) -> Dict[str, Any]:
        return {
            **self._current_area,
            "session_id": self._session_id,
            "generation": self._generation_counter,
        }

    def generate_and_load_trajectories(
        self,
        num_vehicles: int = 15,
        multi_user_ratio: float = 0.5,
        duration_minutes: float = 5.0,
    ) -> Dict[str, Any]:
        area = self._current_area
        dataset, gt_map = generator.generate_area_trajectories(
            center_lat=area["latitude"],
            center_lon=area["longitude"],
            radius_meters=area["radius_meters"],
            area_name=area["name"],
            num_vehicles=num_vehicles,
            multi_user_ratio=multi_user_ratio,
            duration_minutes=duration_minutes,
        )
        return replay_engine.load_dataset(dataset, gt_map)

    def get_clustering_snapshot(self) -> Dict[str, Any]:
        """
        Runs vehicle observation adapter on current simulated vehicles,
        performs DBSCAN vehicle clustering, maps road edge density, and computes ground truth evaluation.
        Safe against temporary failures.
        """
        area = self._current_area
        c_lat, c_lon = area["latitude"], area["longitude"]
        radius_m = float(area.get("radius_meters", 1000.0))

        try:
            # 1. Fetch user observations via READ-ONLY Vehicle Observation Adapter
            from .simulation.vehicle_observation_adapter import vehicle_observation_adapter
            obs_res = vehicle_observation_adapter.get_user_observations_for_area(
                c_lat, c_lon, radius_m
            )
            
            user_obs = obs_res.get("user_observations", [])
            gt_vehicles = obs_res.get("ground_truth_vehicles", [])
            actual_vehicle_count = len(gt_vehicles)

            # 2. Run DBSCAN vehicle clustering (WITHOUT ground truth vehicle IDs, passing radius_meters)
            cluster_res = vehicle_cluster_service.compute_vehicle_clusters(
                user_obs, c_lat, c_lon, radius_m
            )

            clusters = cluster_res.get("clusters", [])

            # 3. Compute road-level density from estimated vehicle clusters (bounded to radius_meters)
            road_density = cluster_road_mapper.compute_road_density(
                clusters, c_lat, c_lon, radius_m
            )

            # 4. Compute ground truth evaluation using ground_truth_map ONLY
            gt_map = {o["user_id"]: o["vehicle_source_id"] for o in user_obs if "user_id" in o and "vehicle_source_id" in o}
            if not gt_map:
                gt_map = trajectory_store.get_ground_truth_map()

            evaluation = evaluation_engine.evaluate_clustering(
                clusters, gt_map, actual_vehicle_count
            )

            self._generation_counter += 1
            self._last_update_timestamp = time.time()

            snapshot = {
                "status": "LIVE",
                "session_id": self._session_id,
                "generation": self._generation_counter,
                "disclaimer": "Simulation-based live traffic analysis",
                "cycle_interval_seconds": 20,
                "area": area,
                "analysis_area": {
                    "name": area.get("name", "Selected Area"),
                    "latitude": c_lat,
                    "longitude": c_lon,
                    "radius_meters": radius_m,
                },
                "simulation": {
                    "status": obs_res.get("status", "LIVE"),
                    "source": obs_res.get("source", "SIMULATION_STORE"),
                    "global_vehicle_count": obs_res.get("vehicles_before_filter", actual_vehicle_count),
                    "area_vehicle_count": actual_vehicle_count,
                    "vehicles_in_area": actual_vehicle_count,
                    "vehicles_before_filter": obs_res.get("vehicles_before_filter", actual_vehicle_count),
                    "vehicles_after_filter": actual_vehicle_count,
                    "user_observations": len(user_obs),
                    "observation_window_seconds": 5.0,
                },
                "gps": {
                    "area_user_observations": len(user_obs),
                    "users_before_filter": obs_res.get("users_before_filter", len(user_obs)),
                    "users_after_filter": len(user_obs),
                },
                "clustering": {
                    **cluster_res,
                    "clusters": clusters,
                    "estimated_vehicles": len(clusters),
                },
                "road_density": road_density,
                "evaluation": evaluation,
                "window_observations": user_obs,
                "replay": replay_engine.get_status(),
            }

            self._last_snapshot = snapshot
            return snapshot

        except Exception as err:
            logger.error("Error computing clustering snapshot: %s", err, exc_info=True)
            if self._last_snapshot:
                fallback = dict(self._last_snapshot)
                fallback["status"] = "UPDATING"
                return fallback
            
            return {
                "status": "TEMPORARY_ANALYSIS_ERROR",
                "session_id": self._session_id,
                "generation": self._generation_counter,
                "error": str(err),
                "area": area,
                "analysis_area": {
                    "name": area.get("name", "Selected Area"),
                    "latitude": c_lat,
                    "longitude": c_lon,
                    "radius_meters": radius_m,
                },
                "simulation": {"status": "UNAVAILABLE", "global_vehicle_count": 0, "area_vehicle_count": 0, "vehicles_in_area": 0, "user_observations": 0},
                "gps": {"area_user_observations": 0, "users_before_filter": 0, "users_after_filter": 0},
                "clustering": {"status": "INACTIVE", "clusters": [], "estimated_vehicles": 0, "metrics": {}},
                "road_density": {"status": "INACTIVE", "road_segments": []},
                "evaluation": {"status": "INACTIVE"},
                "window_observations": [],
            }

    def get_real_traffic(self, fetch_fn=None) -> Dict[str, Any]:
        area = self._current_area
        fn = fetch_fn or get_area_traffic
        raw_traffic = fn(
            area["latitude"], area["longitude"], area["radius_meters"]
        )
        return map_traffic_payload(raw_traffic)


live_clustering_service = LiveClusteringService()


