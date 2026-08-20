import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'routeflow-secret-key-change-in-prod-32bytes')
    AUTH_SECRET = os.environ.get('AUTH_SECRET', os.environ.get('SECRET_KEY', 'routeflow-auth-secret-key-change-in-prod-32bytes'))
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
    REFRESH_TOKEN_EXPIRATION_DAYS = int(os.environ.get('REFRESH_TOKEN_EXPIRATION_DAYS', 7))
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'mock-google-client-id')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'mock-google-client-secret')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/google/callback')
    _raw_cors = os.environ.get('CORS_ORIGINS', '')
    if not _raw_cors or _raw_cors.strip() == '*':
        CORS_ORIGINS = [
            r"^http://localhost(:\d+)?$",
            r"^http://127\.0\.0\.1(:\d+)?$"
        ]
    else:
        CORS_ORIGINS = [o.strip() for o in _raw_cors.split(',') if o.strip()]
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 30.0},
        "pool_pre_ping": True,
    }
    
    # Traffic Intelligence: DBSCAN Clustering
    DBSCAN_EPS_METERS = int(os.environ.get('DBSCAN_EPS_METERS', 500))
    DBSCAN_MIN_SAMPLES = int(os.environ.get('DBSCAN_MIN_SAMPLES', 5))
    
    # Traffic Intelligence: Hotspot Detection
    HOTSPOT_MIN_VEHICLES = int(os.environ.get('HOTSPOT_MIN_VEHICLES', 5))
    HOTSPOT_MIN_DENSITY = float(os.environ.get('HOTSPOT_MIN_DENSITY', 10.0))
    HOTSPOT_MAX_AVERAGE_SPEED = float(os.environ.get('HOTSPOT_MAX_AVERAGE_SPEED', 60.0))
    HOTSPOT_LOW_THRESHOLD = float(os.environ.get('HOTSPOT_LOW_THRESHOLD', 0.35))
    HOTSPOT_HIGH_THRESHOLD = float(os.environ.get('HOTSPOT_HIGH_THRESHOLD', 0.70))

    # Normalization ceilings for hotspot scoring (base defaults)
    HOTSPOT_MAX_EXPECTED_VEHICLES = float(os.environ.get('HOTSPOT_MAX_EXPECTED_VEHICLES', 50.0))
    HOTSPOT_MAX_EXPECTED_DENSITY = float(os.environ.get('HOTSPOT_MAX_EXPECTED_DENSITY', 200.0))

    # Traffic Cost Engine Penalties
    TRAFFIC_PENALTY_FACTOR_LOW = float(os.environ.get('TRAFFIC_PENALTY_FACTOR_LOW', 1.15))
    TRAFFIC_PENALTY_FACTOR_MEDIUM = float(os.environ.get('TRAFFIC_PENALTY_FACTOR_MEDIUM', 1.60))
    TRAFFIC_PENALTY_FACTOR_HIGH = float(os.environ.get('TRAFFIC_PENALTY_FACTOR_HIGH', 3.00))
    TRAFFIC_MIN_EDGE_VEHICLES = int(os.environ.get('TRAFFIC_MIN_EDGE_VEHICLES', 1))

    # Dynamic Traffic-Aware Rerouting (Sprint 11)
    REROUTE_COOLDOWN_SECONDS = int(os.environ.get('REROUTE_COOLDOWN_SECONDS', 15))
    COST_CHANGE_THRESHOLD = float(os.environ.get('COST_CHANGE_THRESHOLD', 0.15))
    MIN_ROUTE_IMPROVEMENT = float(os.environ.get('MIN_ROUTE_IMPROVEMENT', 0.10))
    TRAFFIC_CHANGE_THRESHOLD = int(os.environ.get('TRAFFIC_CHANGE_THRESHOLD', 1))

    # Sprint 11A specific configuration names
    MIN_TRAFFIC_COST_INCREASE_PERCENT = float(os.environ.get('MIN_TRAFFIC_COST_INCREASE_PERCENT', 0.15))
    MIN_ETA_INCREASE_PERCENT = float(os.environ.get('MIN_ETA_INCREASE_PERCENT', 0.15))
    MIN_TRAFFIC_CHANGE_LEVEL = os.environ.get('MIN_TRAFFIC_CHANGE_LEVEL', 'MEDIUM')
    MIN_ROUTE_IMPROVEMENT_PERCENT = float(os.environ.get('MIN_ROUTE_IMPROVEMENT_PERCENT', 0.10))

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'routeflow_dev.db')}")

    # Calibrated overrides for live route-based simulation
    DBSCAN_EPS_METERS = 200
    DBSCAN_MIN_SAMPLES = 3
    HOTSPOT_MIN_VEHICLES = 3
    HOTSPOT_MIN_DENSITY = 5.0
    HOTSPOT_MAX_AVERAGE_SPEED = 80.0
    HOTSPOT_LOW_THRESHOLD = 0.25
    HOTSPOT_HIGH_THRESHOLD = 0.60
    HOTSPOT_MAX_EXPECTED_VEHICLES = 80.0
    HOTSPOT_MAX_EXPECTED_DENSITY = 80.0

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    PRESERVE_CONTEXT_ON_EXCEPTION = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'routeflow.db')}")

    # Calibrated overrides for live route-based simulation
    DBSCAN_EPS_METERS = 200
    DBSCAN_MIN_SAMPLES = 3
    HOTSPOT_MIN_VEHICLES = 3
    HOTSPOT_MIN_DENSITY = 5.0
    HOTSPOT_MAX_AVERAGE_SPEED = 80.0
    HOTSPOT_LOW_THRESHOLD = 0.25
    HOTSPOT_HIGH_THRESHOLD = 0.60
    HOTSPOT_MAX_EXPECTED_VEHICLES = 80.0
    HOTSPOT_MAX_EXPECTED_DENSITY = 80.0


config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)
