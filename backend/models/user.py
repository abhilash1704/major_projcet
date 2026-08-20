import re
from database.db import db
from .base_model import BaseModel, SoftDeleteMixin
from sqlalchemy.orm import validates

class User(BaseModel, SoftDeleteMixin):
    __tablename__ = 'users'

    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    auth_provider = db.Column(db.String(50), nullable=False, default='local')
    profile_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active')

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    @validates('email')
    def validate_email(self, key, address):
        if not address:
            raise ValueError("Email is required")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", address):
            raise ValueError("Invalid email address provided")
        return address.lower().strip()

    @validates('full_name')
    def validate_full_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("Full Name is required")
        return str(value).strip()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.full_name,
            "full_name": self.full_name,
            "email": self.email,
            "profile_image": self.profile_image,
            "provider": self.auth_provider or "local",
            "auth_provider": self.auth_provider or "local",
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }