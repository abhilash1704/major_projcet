import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app import create_app
from database.db import db
from models.user import User

def seed_database():
    app = create_app()
    with app.app_context():
        # Assumes tables are already created via migrations
        if not User.query.first():
            print("Seeding initial users...")
            admin = User(
                full_name="System Admin",
                email="admin@routeflow.com",
                password_hash="hashed_password_placeholder",
                status="active"
            )
            db.session.add(admin)
            db.session.commit()
            print("Seeding complete.")
        else:
            print("Database already seeded.")

if __name__ == "__main__":
    seed_database()
