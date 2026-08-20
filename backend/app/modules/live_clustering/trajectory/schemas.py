"""
Trajectory Replay Schemas and Models
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass
class Observation:
    observation_id: str
    user_id: str
    timestamp: str  # ISO 8601 UTC
    latitude: float
    longitude: float
    speed_kmh: float
    heading: float
    accuracy_m: float
    road_edge_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GroundTruthVehicle:
    vehicle_id: str
    user_ids: List[str]
    start_node: str
    end_node: str
    path_nodes: List[str]
    base_speed_kmh: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TrajectoryDataset:
    dataset_id: str
    area_name: str
    center_lat: float
    center_lon: float
    radius_meters: float
    vehicle_count: int
    user_count: int
    total_observations: int
    vehicles: List[GroundTruthVehicle]
    observations: List[Observation]
    
    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "area_name": self.area_name,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "radius_meters": self.radius_meters,
            "vehicle_count": self.vehicle_count,
            "user_count": self.user_count,
            "total_observations": self.total_observations,
        }
