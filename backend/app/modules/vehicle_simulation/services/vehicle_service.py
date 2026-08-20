"""
VehicleService — Sprint 4.1

Provides CRUD operations for Vehicle records in the SQLite database.
Business logic only — no Flask request/response handling here.
"""
import logging
import uuid
from datetime import datetime, timezone

from database.db import db
from ..models.vehicle import Vehicle, _generate_vehicle_id
from ..schemas.vehicle_schema import VehicleSchema
from ..constants import VALID_VEHICLE_STATUSES, VEHICLE_STATUS_ACTIVE


class VehicleService:
    """
    Service layer for Vehicle CRUD operations.

    All methods raise ValueError for invalid input and RuntimeError for
    unexpected database failures. Routes should catch these and return
    appropriate HTTP responses.
    """

    def _get_logger(self):
        return logging.getLogger("routeflow.vehicle_simulation.service")

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_vehicle(self, data: dict) -> Vehicle:
        """
        Create and persist a new Vehicle record.

        Args:
            data: dict with keys:
                - latitude (required)
                - longitude (required)
                - speed (optional, default 0.0)
                - heading (optional, default 0.0)
                - current_node (optional)
                - current_edge (optional)
                - status (optional, default 'active')
                - vehicle_id (optional — auto-generated if absent)

        Returns:
            Persisted Vehicle instance.

        Raises:
            ValueError: If required fields are missing or validation fails.
        """
        logger = self._get_logger()

        # Validate required coordinate fields
        if data.get("latitude") is None or data.get("longitude") is None:
            raise ValueError("'latitude' and 'longitude' are required fields.")

        try:
            lat = float(data["latitude"])
            lon = float(data["longitude"])
        except (TypeError, ValueError):
            raise ValueError("'latitude' and 'longitude' must be numeric values.")

        speed   = float(data.get("speed",   0.0))
        heading = float(data.get("heading", 0.0))
        status  = data.get("status", VEHICLE_STATUS_ACTIVE)

        if status not in VALID_VEHICLE_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Valid statuses: {sorted(VALID_VEHICLE_STATUSES)}"
            )

        vehicle_id = data.get("vehicle_id") or _generate_vehicle_id()

        vehicle = Vehicle(
            vehicle_id    = vehicle_id,
            latitude      = lat,
            longitude     = lon,
            speed         = speed,
            heading       = heading,
            current_node  = data.get("current_node"),
            current_edge  = data.get("current_edge"),
            edge_progress = float(data.get("edge_progress", 0.0)),
            status        = status,
        )

        try:
            db.session.add(vehicle)
            db.session.commit()
            logger.info("Created vehicle: %s", vehicle.vehicle_id)
            return vehicle
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to create vehicle: %s", str(exc))
            raise RuntimeError(f"Database error creating vehicle: {exc}") from exc

    # ── READ ──────────────────────────────────────────────────────────────────

    def get_vehicle(self, vehicle_id: str) -> Vehicle | None:
        """
        Retrieve a single Vehicle by its ID.

        Returns None if not found.
        """
        return db.session.get(Vehicle, vehicle_id)

    def get_all_vehicles(self) -> list[Vehicle]:
        """
        Retrieve all Vehicle records (no soft-delete — vehicles are explicitly deleted).
        """
        return db.session.execute(db.select(Vehicle)).scalars().all()

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_vehicle_position(self, vehicle_id: str, data: dict) -> Vehicle:
        """
        Update the position and kinematic state of a Vehicle.

        Accepted fields: latitude, longitude, speed, heading,
                         current_node, current_edge, status.

        Returns the updated Vehicle.
        Raises ValueError if the vehicle does not exist or validation fails.
        """
        vehicle = self.get_vehicle(vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle '{vehicle_id}' not found.")

        updatable = ("latitude", "longitude", "speed", "heading",
                     "current_node", "current_edge", "edge_progress", "status")

        for field in updatable:
            if field in data:
                setattr(vehicle, field, data[field])

        vehicle.updated_at = datetime.now(timezone.utc)

        try:
            db.session.commit()
            return vehicle
        except Exception as exc:
            db.session.rollback()
            raise RuntimeError(f"Database error updating vehicle: {exc}") from exc

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete_vehicle(self, vehicle_id: str) -> bool:
        """
        Permanently delete a Vehicle record.

        Returns True if deleted, False if not found.
        """
        vehicle = self.get_vehicle(vehicle_id)
        if vehicle is None:
            return False

        try:
            db.session.delete(vehicle)
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            raise RuntimeError(f"Database error deleting vehicle: {exc}") from exc

    def delete_all_vehicles(self) -> int:
        """
        Delete ALL vehicle records (simulation reset).

        Returns the count of deleted rows.
        Does NOT affect users, road graph, or auth data.
        """
        logger = self._get_logger()
        try:
            count = db.session.execute(db.delete(Vehicle)).rowcount
            db.session.commit()
            logger.info("Simulation cleared: deleted %d vehicle records.", count)
            return count
        except Exception as exc:
            db.session.rollback()
            raise RuntimeError(f"Database error clearing vehicles: {exc}") from exc

    # ── BULK INSERT ───────────────────────────────────────────────────────────

    def bulk_create_vehicles(self, vehicle_data_list: list[dict]) -> tuple[list[Vehicle], int]:
        """
        Efficiently create multiple vehicles in a single database transaction.

        Args:
            vehicle_data_list: list of dicts, each conforming to create_vehicle() input.

        Returns:
            (created_vehicles, failed_count) tuple.
        """
        logger = self._get_logger()
        created = []
        failed  = 0

        vehicles_to_add = []
        for data in vehicle_data_list:
            try:
                lat = float(data["latitude"])
                lon = float(data["longitude"])
                status = data.get("status", VEHICLE_STATUS_ACTIVE)
                if status not in VALID_VEHICLE_STATUSES:
                    raise ValueError(f"Invalid status: {status}")

                v = Vehicle(
                    vehicle_id    = data.get("vehicle_id") or _generate_vehicle_id(),
                    latitude      = lat,
                    longitude     = lon,
                    speed         = float(data.get("speed", 0.0)),
                    heading       = float(data.get("heading", 0.0)),
                    current_node  = data.get("current_node"),
                    current_edge  = data.get("current_edge"),
                    edge_progress = float(data.get("edge_progress", 0.0)),
                    status        = status,
                )
                vehicles_to_add.append(v)
            except Exception as exc:
                logger.warning("Skipping invalid vehicle data: %s — %s", data, exc)
                failed += 1

        try:
            db.session.add_all(vehicles_to_add)
            db.session.commit()
            created = vehicles_to_add
        except Exception as exc:
            db.session.rollback()
            logger.error("Bulk vehicle insert failed: %s", exc)
            failed += len(vehicles_to_add)
            created = []

        logger.info(
            "Bulk create: %d created, %d failed (total attempted %d).",
            len(created), failed, len(vehicle_data_list)
        )
        return created, failed


vehicle_service = VehicleService()
