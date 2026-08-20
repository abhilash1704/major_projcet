class RoadEdge:
    """
    Conceptual representation of a Road Network Edge (connecting two RoadNodes).
    Contains topological connection (source, target) and edge metrics.
    """
    def __init__(
        self,
        source,
        target,
        distance=None,
        road_type="default",
        speed_limit=None,
        travel_time=None,
        name=None,
        oneway=False,
        geometry=None
    ):
        self.source = str(source)
        self.target = str(target)
        self.distance = float(distance) if distance is not None else 0.0
        self.road_type = road_type
        self.speed_limit = float(speed_limit) if speed_limit is not None else 40.0
        self.travel_time = float(travel_time) if travel_time is not None else 0.0
        self.name = name or ""
        self.oneway = bool(oneway)
        self.geometry = geometry or []

    def to_dict(self):
        return {
            "source": self.source,
            "target": self.target,
            "distance": self.distance,
            "road_type": self.road_type,
            "speed_limit": self.speed_limit,
            "travel_time": self.travel_time,
            "name": self.name,
            "oneway": self.oneway,
            "geometry": self.geometry
        }

    def __repr__(self):
        return f"<RoadEdge {self.source} -> {self.target} ({self.road_type}, dist={self.distance}km)>"
