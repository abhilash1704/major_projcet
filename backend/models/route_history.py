from database.db import db
from .base_model import BaseModel, SoftDeleteMixin

class RouteHistory(BaseModel, SoftDeleteMixin):
    __tablename__ = 'route_history'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    source_name = db.Column(db.String(255), nullable=True)
    source_latitude = db.Column(db.Float, nullable=True)
    source_longitude = db.Column(db.Float, nullable=True)
    destination_name = db.Column(db.String(255), nullable=True)
    destination_latitude = db.Column(db.Float, nullable=True)
    destination_longitude = db.Column(db.Float, nullable=True)
    distance_km = db.Column(db.Float, nullable=True)
    eta_minutes = db.Column(db.Float, nullable=True)
    algorithm = db.Column(db.String(50), nullable=True)
    routing_mode = db.Column(db.String(50), nullable=True)
    traffic_level = db.Column(db.String(50), nullable=True)
    traffic_penalty = db.Column(db.Float, nullable=True)
    route_status = db.Column(db.String(50), default='COMPLETED')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_name": self.source_name,
            "source_latitude": self.source_latitude,
            "source_longitude": self.source_longitude,
            "destination_name": self.destination_name,
            "destination_latitude": self.destination_latitude,
            "destination_longitude": self.destination_longitude,
            "distance_km": self.distance_km,
            "eta_minutes": self.eta_minutes,
            "algorithm": self.algorithm,
            "routing_mode": self.routing_mode,
            "traffic_level": self.traffic_level,
            "traffic_penalty": self.traffic_penalty,
            "route_status": self.route_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
