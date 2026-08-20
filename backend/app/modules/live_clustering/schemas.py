"""
Live Clustering Module Schemas
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass
class AreaSelectionRequest:
    area_id: Optional[str] = None
    name: Optional[str] = None
    latitude: float = 12.9698
    longitude: float = 77.7499
    radius_meters: float = 1000.0
    source: str = "preset"

@dataclass
class TrajectoryGenerateRequest:
    area_name: str = "Selected Area"
    latitude: float = 12.9698
    longitude: float = 77.7499
    radius_meters: float = 1000.0
    num_vehicles: int = 15
    multi_user_ratio: float = 0.5
    duration_minutes: float = 5.0
