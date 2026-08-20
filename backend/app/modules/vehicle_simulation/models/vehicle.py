"""
Vehicle SQLAlchemy Model — Sprint 4.1

Represents a single simulated vehicle in the SQLite database.
Stores vehicle identity, geographic position, kinematic state,
and references to the road-network graph (current_node / current_edge).

The NetworkX graph itself is NOT stored here — only string references
that can be resolved via the existing GraphService at runtime.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from database.db import db
from ..constants import VALID_VEHICLE_STATUSES, VEHICLE_ID_PREFIX, VEHICLE_STATUS_ACTIVE


def _generate_vehicle_id():
    """Generates a prefixed unique vehicle identifier: veh_<uuid4>."""
    return f"{VEHICLE_ID_PREFIX}{uuid.uuid4().hex}"


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    # Primary key — prefixed UUID string (e.g. "veh_a1b2c3…")
    vehicle_id = db.Column(db.String(64), primary_key=True, default=_generate_vehicle_id, unique=True, nullable=False)

    # Geographic position
    latitude  = db.Column(db.Float(precision=8), nullable=False)
    longitude = db.Column(db.Float(precision=8), nullable=False)

    # Kinematic state
    speed   = db.Column(db.Float, nullable=False, default=0.0)   # km/h
    heading = db.Column(db.Float, nullable=False, default=0.0)   # degrees 0–360

    # Road network references (string keys into the NetworkX graph)
    current_node = db.Column(db.String(64), nullable=True)
    current_edge = db.Column(db.String(128), nullable=True)

    # Sprint 4.3 — tracks fractional progress along current_edge [0.0, 1.0]
    edge_progress = db.Column(db.Float, nullable=False, default=0.0)

    # Sprint 6.5 — ties vehicle to a specific simulation session
    simulation_id = db.Column(db.String(64), nullable=True, index=True)

    # Lifecycle
    status = db.Column(db.String(20), nullable=False, default=VEHICLE_STATUS_ACTIVE)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── SQLAlchemy validators ────────────────────────────────────────────────

    @validates("latitude")
    def validate_latitude(self, key, value):
        lat = float(value)
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"latitude must be between -90 and 90, got {lat}")
        return lat

    @validates("longitude")
    def validate_longitude(self, key, value):
        lon = float(value)
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"longitude must be between -180 and 180, got {lon}")
        return lon

    @validates("speed")
    def validate_speed(self, key, value):
        spd = float(value)
        if spd < 0:
            raise ValueError(f"speed must be >= 0, got {spd}")
        return spd

    @validates("heading")
    def validate_heading(self, key, value):
        hdg = float(value)
        if not (0.0 <= hdg < 360.0):
            raise ValueError(f"heading must be in [0, 360), got {hdg}")
        return hdg

    @validates("status")
    def validate_status(self, key, value):
        if value not in VALID_VEHICLE_STATUSES:
            raise ValueError(
                f"status '{value}' is invalid. Must be one of: {sorted(VALID_VEHICLE_STATUSES)}"
            )
        return value

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self):
        """Returns a clean dictionary for API responses."""
        return {
            "vehicle_id":    self.vehicle_id,
            "simulation_id": self.simulation_id,
            "latitude":      self.latitude,
            "longitude":     self.longitude,
            "speed":         self.speed,
            "heading":       self.heading,
            "current_node":  self.current_node,
            "current_edge":  self.current_edge,
            "edge_progress": self.edge_progress,
            "status":        self.status,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<Vehicle id={self.vehicle_id} "
            f"({self.latitude:.5f}, {self.longitude:.5f}) "
            f"spd={self.speed:.1f} hdg={self.heading:.1f} "
            f"status={self.status}>"
        )
