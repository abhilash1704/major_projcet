"""
Traffic Intelligence Routes — Sprint 6 / Sprint 8 / Sprint 9A

Provides endpoints for live simulated vehicle positions, spatial density,
DBSCAN clustering, hotspot detection, and traffic-aware road edge costs.
"""
import logging
from flask import Blueprint, jsonify, request
from .services import traffic_data_service, traffic_density_service
from core.errors import APIError

traffic_intelligence_bp = Blueprint(
    'traffic_intelligence', __name__, url_prefix='/api/traffic-intelligence'
)

logger = logging.getLogger("routeflow.traffic_intelligence.routes")


@traffic_intelligence_bp.route('/vehicles', methods=['GET'])
def get_live_vehicles():
    """
    GET /api/traffic-intelligence/vehicles
    Returns a read-only snapshot of current live simulated vehicle positions.
    """
    try:
        snapshot = traffic_data_service.get_active_vehicle_snapshot()
        return jsonify({"success": True, **snapshot}), 200
    except Exception as exc:
        logger.error("Vehicle snapshot failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "VEHICLE_STATE_UNAVAILABLE",
            "message": "Vehicle simulation state is currently unavailable."
        }), 503


@traffic_intelligence_bp.route('/density', methods=['GET'])
def get_traffic_density():
    """
    GET /api/traffic-intelligence/density
    Returns a spatial density grid based on current live simulated vehicle positions.
    Query parameters:
        - cell_size_meters: int (default 500)
    """
    try:
        cell_size = request.args.get('cell_size_meters', default=500, type=int)
        if cell_size <= 0:
            return jsonify({
                "success": False,
                "error": "INVALID_PARAMETER",
                "message": "cell_size_meters must be a positive integer."
            }), 400
            
        density_data = traffic_density_service.calculate_density(cell_size_meters=cell_size)
        return jsonify({"success": True, **density_data}), 200
    except Exception as exc:
        logger.error("Density calculation failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "DENSITY_CALCULATION_FAILED",
            "message": "Failed to calculate traffic density from vehicle state."
        }), 503


@traffic_intelligence_bp.route('/clusters', methods=['GET'])
def get_traffic_clusters():
    """
    GET /api/traffic-intelligence/clusters
    Returns spatial clusters of live vehicles using DBSCAN.
    Includes per-cluster density_level for ClusterLayer visualization.
    """
    try:
        from .services import dbscan_service
        cluster_data = dbscan_service.get_clusters()
        return jsonify(cluster_data), 200
    except Exception as exc:
        logger.error("Clustering failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "CLUSTERING_FAILED",
            "message": "Unable to calculate traffic clusters."
        }), 503


@traffic_intelligence_bp.route('/hotspots', methods=['GET'])
def get_traffic_hotspots():
    """
    GET /api/traffic-intelligence/hotspots
    Returns significant traffic hotspots by analyzing DBSCAN clusters.
    Includes global_traffic_level (authoritative, backend-computed).
    """
    try:
        from .services import hotspot_service
        hotspot_data = hotspot_service.detect_hotspots()
        return jsonify(hotspot_data), 200
    except Exception as exc:
        logger.error("Hotspot detection failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "HOTSPOT_DETECTION_FAILED",
            "message": "Unable to calculate traffic hotspots."
        }), 503


@traffic_intelligence_bp.route('/costs', methods=['GET'])
def get_traffic_costs():
    """
    GET /api/traffic-intelligence/costs — Sprint 9A
    Returns traffic-aware road edge costs and penalty metrics.
    """
    try:
        from .services import traffic_cost_service
        cost_data = traffic_cost_service.calculate_traffic_costs()
        return jsonify(cost_data), 200
    except Exception as exc:
        logger.error("Traffic cost calculation failed: %s", exc)
        return jsonify({
            "success": False,
            "error": "TRAFFIC_COST_CALCULATION_FAILED",
            "message": "Unable to calculate traffic-aware road costs."
        }), 503
