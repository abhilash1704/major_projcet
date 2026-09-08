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
from app.modules.live_clustering.spatial_filter import (
    haversine_distance_meters,
    filter_vehicles_to_analysis_area,
    filter_observations_to_analysis_area,
)

from app.modules.live_clustering.trajectory.generator import generator as trajectory_generator

logger = logging.getLogger("routeflow.live_clustering.vehicle_observation_adapter")


class VehicleObservationAdapter:
    """
    Reads active simulated vehicles in READ-ONLY mode and adapts them into
    virtual GPS user observations filtered strictly by selectedArea center and radius_meters.
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
        Enforces Stage 1 + Stage 2 spatial validation on both vehicles and user observations.
        """
        snapshot = simulation_store.get_snapshot()
        all_vehicles = snapshot.get("vehicles", [])
        sim_status = snapshot.get("status", "IDLE")

        # Stage 1 + 2 Vehicle Filtering via shared spatial_filter function
        vehicles_in_area = filter_vehicles_to_analysis_area(
            all_vehicles, center_lat, center_lon, radius_meters
        )

        vehicles_before_filter = len(all_vehicles)
        vehicles_after_filter = len(vehicles_in_area)

        # Dynamic population scaling by radius (Requirement 5)
        if radius_meters <= 600.0:
            num_area_vehicles = 30
        elif radius_meters <= 1200.0:
            num_area_vehicles = 75
        else:
            num_area_vehicles = 150

        # Fallback to Trajectory Generator / Replay Engine if global simulation has no area vehicles
        if len(vehicles_in_area) == 0 and use_generator_fallback:
            replay_snap = replay_engine.get_snapshot()
            if replay_snap.get("status") == "RUNNING" and replay_snap.get("window_observations"):
                raw_obs = replay_snap.get("window_observations", [])
                filtered_obs = filter_observations_to_analysis_area(
                    raw_obs, center_lat, center_lon, radius_meters
                )
                gt_vehicle_ids = list(set(o.get("vehicle_source_id") or o.get("vehicle_id") for o in filtered_obs if o.get("vehicle_source_id") or o.get("vehicle_id")))
                return {
                    "status": "LIVE",
                    "source": "SIMULATION_REPLAY",
                    "vehicles_in_area": len(gt_vehicle_ids),
                    "total_simulated_vehicles": vehicles_before_filter,
                    "vehicles_before_filter": vehicles_before_filter,
                    "vehicles_after_filter": len(gt_vehicle_ids),
                    "users_before_filter": len(raw_obs),
                    "users_after_filter": len(filtered_obs),
                    "user_observations": filtered_obs,
                    "ground_truth_vehicles": gt_vehicle_ids,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            elif use_generator_fallback and replay_snap.get("status") in ("IDLE", "STOPPED", "READY"):
                # Generate synthetic area vehicles on demand strictly inside area
                dataset, gt_map = trajectory_generator.generate_area_trajectories(
                    center_lat=center_lat,
                    center_lon=center_lon,
                    radius_meters=radius_meters,
                    num_vehicles=num_area_vehicles,
                    multi_user_ratio=0.5,
                    duration_minutes=5.0
                )
                replay_engine.load_dataset(dataset, gt_map)
                replay_engine.start()
                time.sleep(0.1)  # Allow background worker frame 0 tick
                replay_snap = replay_engine.get_snapshot()
                raw_obs = replay_snap.get("window_observations", [])
                filtered_obs = filter_observations_to_analysis_area(
                    raw_obs, center_lat, center_lon, radius_meters
                )
                gt_vehicle_ids = list(set(o.get("vehicle_source_id") or o.get("vehicle_id") for o in filtered_obs if o.get("vehicle_source_id") or o.get("vehicle_id")))
                return {
                    "status": "LIVE",
                    "source": "SIMULATION_ADAPTER",
                    "vehicles_in_area": len(gt_vehicle_ids),
                    "total_simulated_vehicles": vehicles_before_filter,
                    "vehicles_before_filter": vehicles_before_filter,
                    "vehicles_after_filter": len(gt_vehicle_ids),
                    "users_before_filter": len(raw_obs),
                    "users_after_filter": len(filtered_obs),
                    "user_observations": filtered_obs,
                    "ground_truth_vehicles": gt_vehicle_ids,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

        # Generate observations for filtered in-area vehicles
        raw_user_observations = []
        gt_vehicle_ids = []
        for v in vehicles_in_area:
            v_id = str(v.get("vehicle_id"))
            gt_vehicle_ids.append(v_id)
            user_obs = generate_user_observations_for_vehicle(v)
            raw_user_observations.extend(user_obs)

        # STAGE 2 OBSERVATION FILTER (Requirement 7: Discard noisy GPS observations pushed outside radius)
        filtered_user_observations = filter_observations_to_analysis_area(
            raw_user_observations, center_lat, center_lon, radius_meters
        )

        return {
            "status": "LIVE" if sim_status in ("RUNNING", "READY") or filtered_user_observations else "IDLE",
            "source": "SIMULATION_STORE",
            "vehicles_in_area": vehicles_after_filter,
            "total_simulated_vehicles": vehicles_before_filter,
            "vehicles_before_filter": vehicles_before_filter,
            "vehicles_after_filter": vehicles_after_filter,
            "users_before_filter": len(raw_user_observations),
            "users_after_filter": len(filtered_user_observations),
            "user_observations": filtered_user_observations,
            "ground_truth_vehicles": gt_vehicle_ids,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

vehicle_observation_adapter = VehicleObservationAdapter()

