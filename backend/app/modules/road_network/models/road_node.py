class RoadNode:
    """
    Conceptual representation of an OpenStreetMap / Road Network Node.
    Contains spatial location (latitude, longitude) and unique node identifier.
    """
    def __init__(self, node_id, latitude, longitude, tags=None):
        self.node_id = str(node_id)
        self.latitude = float(latitude) if latitude is not None else None
        self.longitude = float(longitude) if longitude is not None else None
        self.tags = tags or {}

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "tags": self.tags
        }

    def __repr__(self):
        return f"<RoadNode id={self.node_id} ({self.latitude}, {self.longitude})>"
