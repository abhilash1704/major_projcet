"""
DBSCAN Vehicle Clustering Service
"""
import logging
import threading
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.cluster import DBSCAN

from ..config import CLUSTER_EPS_METERS, CLUSTER_MIN_SAMPLES
from .feature_builder import feature_builder
from .cluster_tracker import cluster_tracker
from .metrics import calculate_clustering_metrics

logger = logging.getLogger("routeflow.live_clustering.clustering.vehicle_cluster_service")


class VehicleClusterService:
    """
    Groups user GPS observations into estimated vehicle clusters using DBSCAN.
    Strictly isolated from ground-truth vehicle identifiers.
    """
    def __init__(self, eps_m: float = CLUSTER_EPS_METERS, min_samples: int = CLUSTER_MIN_SAMPLES):
        self._lock = threading.RLock()
        self._eps_m = eps_m
        self._min_samples = min_samples

    def compute_vehicle_clusters(
        self,
        observations: List[Dict[str, Any]],
        center_lat: float,
        center_lon: float
    ) -> Dict[str, Any]:
        with self._lock:
            if not observations:
                cluster_tracker.reset()
                return {
                    "status": "INACTIVE",
                    "clusters": [],
                    "metrics": calculate_clustering_metrics(0, [], 0),
                }

            # 1. Build feature matrix (WITHOUT ground truth vehicle ID)
            features, valid_obs = feature_builder.build_feature_matrix(
                observations, center_lat, center_lon
            )

            if len(valid_obs) == 0 or features.shape[0] == 0:
                return {
                    "status": "INACTIVE",
                    "clusters": [],
                    "metrics": calculate_clustering_metrics(0, [], 0),
                }

            # 2. Fit DBSCAN
            db = DBSCAN(eps=self._eps_m, min_samples=self._min_samples)
            labels = db.fit_predict(features)

            # 3. Group by cluster label
            clusters_map: Dict[int, List[Dict[str, Any]]] = {}
            noise_obs: List[Dict[str, Any]] = []

            for idx, label in enumerate(labels):
                obs = valid_obs[idx]
                if label == -1:
                    noise_obs.append(obs)
                else:
                    if label not in clusters_map:
                        clusters_map[label] = []
                    clusters_map[label].append(obs)

            # 4. Build output cluster objects with ID stability
            clusters: List[Dict[str, Any]] = []

            for label, clus_obs in clusters_map.items():
                user_ids = sorted(list({o.get("user_id", "unknown") for o in clus_obs}))
                obs_ids = [o.get("observation_id") for o in clus_obs if o.get("observation_id")]

                avg_lat = sum(float(o["latitude"]) for o in clus_obs) / len(clus_obs)
                avg_lon = sum(float(o["longitude"]) for o in clus_obs) / len(clus_obs)

                speeds = [float(o["speed_kmh"]) for o in clus_obs if o.get("speed_kmh") is not None]
                headings = [float(o["heading"]) for o in clus_obs if o.get("heading") is not None]
                road_edges = [o.get("road_edge_id") for o in clus_obs if o.get("road_edge_id")]

                avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
                avg_heading = sum(headings) / len(headings) if headings else 0.0
                primary_edge = max(set(road_edges), key=road_edges.count) if road_edges else None

                matched_id = cluster_tracker.match_or_create_id(user_ids, avg_lat, avg_lon)

                cluster_obj = {
                    "cluster_id": matched_id,
                    "user_count": len(user_ids),
                    "user_ids": user_ids,
                    "observation_ids": obs_ids,
                    "center_latitude": round(avg_lat, 6),
                    "center_longitude": round(avg_lon, 6),
                    "average_speed_kmh": round(avg_speed, 1),
                    "average_heading": round(avg_heading, 1),
                    "primary_road_edge_id": primary_edge,
                    "observations": clus_obs,
                }
                clusters.append(cluster_obj)

            cluster_tracker.update_registry(clusters)
            metrics = calculate_clustering_metrics(len(valid_obs), clusters, len(noise_obs))

            return {
                "status": "ACTIVE",
                "clusters": clusters,
                "metrics": metrics,
            }


vehicle_cluster_service = VehicleClusterService()
