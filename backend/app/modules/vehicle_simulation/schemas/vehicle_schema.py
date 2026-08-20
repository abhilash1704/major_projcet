"""
VehicleSchema — Sprint 4.1

Serialises Vehicle model instances into clean API response dictionaries.
Does not expose internal database metadata.
"""


class VehicleSchema:
    """Converts a Vehicle ORM instance to a normalized API response dict."""

    @staticmethod
    def dump(vehicle):
        """
        Serialise a single Vehicle instance.

        Args:
            vehicle: Vehicle ORM object

        Returns:
            dict with normalised vehicle fields, or None if vehicle is None.
        """
        if vehicle is None:
            return None
        return {
            "vehicle_id":   vehicle.vehicle_id,
            "latitude":     vehicle.latitude,
            "longitude":    vehicle.longitude,
            "speed":        vehicle.speed,
            "heading":      vehicle.heading,
            "current_node": vehicle.current_node,
            "current_edge": vehicle.current_edge,
            "edge_progress": getattr(vehicle, "edge_progress", 0.0),
            "status":       vehicle.status,
        }

    @staticmethod
    def dump_many(vehicles):
        """
        Serialise a list of Vehicle instances.

        Args:
            vehicles: iterable of Vehicle ORM objects

        Returns:
            list of dicts
        """
        return [VehicleSchema.dump(v) for v in vehicles if v is not None]
