import os
from flask import Flask, jsonify
from flask_cors import CORS
from config.config import config_by_name
from database.db import db, init_db
from core.errors import register_error_handlers
from core.logger import setup_logger

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'dev')
        
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    app.config.from_object(config_by_name[config_name])
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    # Setup CORS
    CORS(
        app,
        resources={r"/*": {"origins": app.config['CORS_ORIGINS']}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    
    # Initialize Database and Migrate
    init_db(app)
    
    # Import models for Flask-Migrate (all models must be imported here)
    from models import User, RouteHistory
    from app.modules.vehicle_simulation.models import Vehicle  # noqa: F401
    from app.modules.auth.models import RefreshToken, PasswordResetToken  # noqa: F401

    with app.app_context():
        db.create_all()
    
    # Setup Logging
    setup_logger(app)
    
    # Register Error Handlers
    register_error_handlers(app)
    
    # Register Blueprints
    from api.v1 import api_v1
    app.register_blueprint(api_v1)

    from app.modules.road_network.routes import road_network_bp
    app.register_blueprint(road_network_bp)

    from app.modules.vehicle_simulation.routes import vehicle_simulation_bp
    app.register_blueprint(vehicle_simulation_bp)

    from api.routes_blueprint import routes_bp
    app.register_blueprint(routes_bp)

    from app.modules.traffic_intelligence.routes import traffic_intelligence_bp
    app.register_blueprint(traffic_intelligence_bp)

    from app.modules.live_clustering.routes import live_clustering_bp
    app.register_blueprint(live_clustering_bp)

    from app.modules.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.modules.history.routes import history_bp
    app.register_blueprint(history_bp)


    # ── Graph preloading (runs once at startup) ────────────────────────────
    # Loads the pre-built road network from disk cache and builds the
    # cKDTree spatial index so route requests incur 0 ms graph load time.
    with app.app_context():
        try:
            from app.modules.road_network.services.graph_service import graph_service
            graph_service.preload_default_graph()
        except Exception as exc:
            app.logger.warning("[Graph] Startup preload failed: %s", exc)

    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "name": "RouteFlow API",
            "message": "Welcome to RouteFlow API. Please use /api/v1/ for endpoints."
        })

    return app
