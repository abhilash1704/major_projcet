"""
Vehicle Observation Adapter for Live Clustering

READ-ONLY adapter connecting RouteFlow's global Vehicle Simulation store
to the Live Vehicle Clustering module.
"""
import math
import logging
import time
from typing import Dict, Any, List, Optional
from app.modules.vehicle_simulation.services.simulation_store import simulation_store
from app.modules.live_clustering.simulation.user_observation_generator import (
    generate_user_observations_for_vehicle,
)
from app.modules.live_clustering.trajectory.replay_engine import replay_engine
from app.modules.live_clustering.trajectory.generator import trajectory_generator

logger = logging.getLogger("routeflow.live_clustering.vehicle_observation_adapter")

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Haversine distance in meters between two lat/lon points.
    """
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class VehicleObservationAdapter:
    """
    Reads active simulated vehicles in READ-ONLY mode and adapts them into
    virtual GPS user observations filtered by selectedArea.
    """

    def get_user_observations_for_area(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float = 1000.0,
        use_generator_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieves user observations for vehicles within the selected area.
        """
        snapshot = simulation_store.get_snapshot()
        all_vehicles = snapshot.get("vehicles", [])
        sim_status = snapshot.get("status", "IDLE")

        vehicles_in_area = []
        for v in all_vehicles:
            try:
                v_lat = float(v.get("latitude", 0.0))
                v_lon = float(v.get("longitude", 0.0))
                dist = haversine_distance_meters(center_lat, center_lon, v_lat, v_lon)
                if dist <= radius_meters:
                    vehicles_in_area.append(v)
            except (ValueError, TypeError):
                continue

        # Fallback to Trajectory Generator / Replay Engine if global simulation is idle
        if len(vehicles_in_area) == 0 and use_generator_fallback:
            replay_snap = replay_engine.get_snapshot()
            if replay_snap.get("status") == "RUNNING" and replay_snap.get("window_observations"):
                obs_list = replay_snap.get("window_observations", [])
                gt_vehicle_ids = list(set(o.get("vehicle_source_id") for o in obs_list if o.get("vehicle_source_id")))
                return {
                    "status": "LIVE",
                    "source": "SIMULATION_REPLAY",
                    "vehicles_in_area": len(gt_vehicle_ids),
                    "total_simulated_vehicles": len(gt_vehicle_ids),
                    "user_observations": obs_list,
                    "ground_truth_vehicles": gt_vehicle_ids,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            elif use_generator_fallback and replay_snap.get("status") == "IDLE":
                # Generate synthetic area vehicles on demand for seamless area analysis
                dataset, gt_map = trajectory_generator.generate_area_trajectories(
                    center_lat=center_lat,
                    center_lon=center_lon,
                    radius_meters=radius_meters,
                    num_vehicles=12,
                    multi_user_ratio=0.5,
                    duration_minutes=5.0
                )
                replay_engine.load_dataset(dataset, gt_map)
                replay_engine.start()
                replay_snap = replay_engine.get_snapshot()
                obs_list = replay_snap.get("window_observations", [])
                gt_vehicle_ids = list(set(o.get("vehicle_source_id") for o in obs_list if o.get("vehicle_source_id")))
                return {
                    "status": "LIVE",
                    "source": "SIMULATION_ADAPTER",
                    "vehicles_in_area": len(gt_vehicle_ids),
                    "total_simulated_vehicles": len(gt_vehicle_ids),
                    "user_observations": obs_list,
                    "ground_truth_vehicles": gt_vehicle_ids,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

        # Adapt vehicles from active simulation store
        user_observations = []
        gt_vehicle_ids = []
        for v in vehicles_in_area:
            v_id = str(v.get("vehicle_id"))
            gt_vehicle_ids.append(v_id)
            user_obs = generate_user_observations_for_vehicle(v)
            user_observations.extend(user_obs)

        return {
            "status": "LIVE" if sim_status in ("RUNNING", "READY") or user_observations else "IDLE",
            "source": "SIMULATION_STORE",
            "vehicles_in_area": len(vehicles_in_area),
            "total_simulated_vehicles": len(all_vehicles),
            "user_observations": user_observations,
            "ground_truth_vehicles": gt_vehicle_ids,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

vehicle_observation_adapter = VehicleObservationAdapter()
