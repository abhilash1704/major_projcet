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
        allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With", "X-Request-ID", "X-Correlation-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Request correlation hooks
    @app.before_request
    def set_request_context():
        import uuid
        from flask import request, g
        req_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or f"rf_{uuid.uuid4().hex[:12]}"
        )
        g.request_id = req_id

    @app.after_request
    def append_request_headers(response):
        from flask import g
        req_id = getattr(g, "request_id", None)
        if req_id:
            response.headers["X-Request-ID"] = req_id
        return response
    
    # Initialize Database and Migrate
    init_db(app)
    
    # Import models for Flask-Migrate (all models must be imported here)
    from models import User, RouteHistory
    from app.modules.vehicle_simulation.models import Vehicle  # noqa: F401

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

    # Health & Observability endpoint
    @app.route('/api/health', methods=['GET'])
    def api_health():
        import time
        from flask import g
        from sqlalchemy import text

        db_status = "up"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:
            app.logger.warning("[Health] DB check failed: %s", exc)
            db_status = "unavailable"

        routing_status = "ready"
        try:
            from app.modules.road_network.services.graph_service import graph_service
            if not graph_service.is_default_graph_loaded():
                routing_status = "initializing"
        except Exception:
            routing_status = "degraded"

        traffic_provider_status = "active"
        try:
            from app.modules.live_clustering.traffic_provider_service import traffic_circuit_breaker
            traffic_provider_status = traffic_circuit_breaker.state.lower()
        except Exception:
            traffic_provider_status = "unavailable"

        overall = "healthy" if db_status == "up" else "degraded"
        status_code = 200 if overall == "healthy" else 503

        return jsonify({
            "status": overall,
            "success": overall == "healthy",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": getattr(g, "request_id", None),
            "dependencies": {
                "database": db_status,
                "routing_engine": routing_status,
                "traffic_provider": traffic_provider_status,
                "clustering_engine": "ready",
            }
        }), status_code

    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "name": "AlgoRoutes API",
            "message": "Welcome to AlgoRoutes API. Please use /api/v1/ for endpoints."
        })

    return app
