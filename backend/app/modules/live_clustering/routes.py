"""
Live Clustering REST API Routes
"""
import logging
from flask import Blueprint, jsonify, request

from .area.area_service import get_all_areas, get_area_by_id
from .traffic.traffic_provider_service import get_area_traffic
from .trajectory.replay_engine import replay_engine
from .service import live_clustering_service

logger = logging.getLogger("routeflow.live_clustering.routes")

live_clustering_bp = Blueprint("live_clustering", __name__, url_prefix="/api/live-clustering")


@live_clustering_bp.route("/areas", methods=["GET"])
def list_areas():
    """GET /api/live-clustering/areas — 50 Bengaluru Monitoring Areas."""
    return jsonify({
        "status": "success",
        "count": len(get_all_areas()),
        "areas": get_all_areas(),
    }), 200


@live_clustering_bp.route("/search-area", methods=["GET"])
def search_area():
    """GET /api/live-clustering/search-area?q=..."""
    query = request.args.get("q", "").strip().lower()
    areas = get_all_areas()
    if not query:
        return jsonify({"status": "success", "results": areas[:10]}), 200

    results = [
        a for a in areas
        if query in a["name"].lower() or query in a["id"].lower() or query in a.get("category", "").lower()
    ]
    return jsonify({"status": "success", "results": results}), 200


@live_clustering_bp.route("/analyze-area", methods=["POST"])
def analyze_area():
    """
    POST /api/live-clustering/analyze-area
    Selects area & radius for trajectory replay and clustering.
    """
    data = request.get_json() or {}
    lat = data.get("latitude")
    lon = data.get("longitude")
    name = data.get("name", "Selected Area")
    area_id = data.get("area_id")
    radius_m = float(data.get("radius_meters", 1000.0))
    source = data.get("source", "preset")

    if area_id and (lat is None or lon is None):
        area_obj = get_area_by_id(area_id)
        if area_obj:
            lat = area_obj["latitude"]
            lon = area_obj["longitude"]
            name = area_obj["name"]

    if lat is None or lon is None:
        # Default Whitefield
        lat, lon = 12.9698, 77.7499
        name = "Whitefield"

    active_area = live_clustering_service.set_active_area(
        lat=float(lat), lon=float(lon), name=name, area_id=area_id, radius_m=radius_m, source=source
    )
    
    snapshot = live_clustering_service.get_clustering_snapshot()
    return jsonify({
        "status": "success",
        "area": active_area,
        "snapshot": snapshot,
    }), 200


@live_clustering_bp.route("/trajectory/generate", methods=["POST"])
def generate_trajectory():
    """
    POST /api/live-clustering/trajectory/generate
    Generates road-constrained vehicle trajectories inside active area.
    """
    data = request.get_json() or {}
    num_vehicles = int(data.get("num_vehicles", 15))
    multi_user_ratio = float(data.get("multi_user_ratio", 0.5))
    duration_minutes = float(data.get("duration_minutes", 5.0))

    replay_status = live_clustering_service.generate_and_load_trajectories(
        num_vehicles=num_vehicles,
        multi_user_ratio=multi_user_ratio,
        duration_minutes=duration_minutes,
    )
    return jsonify({
        "status": "success",
        "replay": replay_status,
    }), 200


@live_clustering_bp.route("/trajectory/start", methods=["POST"])
def start_replay():
    """POST /api/live-clustering/trajectory/start"""
    status = replay_engine.start()
    return jsonify({"status": "success", "replay": status}), 200


@live_clustering_bp.route("/trajectory/pause", methods=["POST"])
def pause_replay():
    """POST /api/live-clustering/trajectory/pause"""
    status = replay_engine.pause()
    return jsonify({"status": "success", "replay": status}), 200


@live_clustering_bp.route("/trajectory/stop", methods=["POST"])
def stop_replay():
    """POST /api/live-clustering/trajectory/stop"""
    status = replay_engine.stop()
    return jsonify({"status": "success", "replay": status}), 200


@live_clustering_bp.route("/trajectory/speed", methods=["POST"])
def set_replay_speed():
    """POST /api/live-clustering/trajectory/speed"""
    data = request.get_json() or {}
    speed = float(data.get("speed", 1.0))
    status = replay_engine.set_speed(speed)
    return jsonify({"status": "success", "replay": status}), 200


@live_clustering_bp.route("/snapshot", methods=["GET"])
def get_snapshot():
    """GET /api/live-clustering/snapshot — Full Live Vehicle Clustering Snapshot."""
    snapshot = live_clustering_service.get_clustering_snapshot()
    return jsonify({
        "status": "success",
        "snapshot": snapshot,
    }), 200


@live_clustering_bp.route("/vehicle-clusters", methods=["GET"])
def get_vehicle_clusters():
    """GET /api/live-clustering/vehicle-clusters"""
    snapshot = live_clustering_service.get_clustering_snapshot()
    return jsonify({
        "status": "success",
        "clustering": snapshot.get("clustering", {}),
    }), 200


@live_clustering_bp.route("/road-density", methods=["GET"])
def get_road_density():
    """GET /api/live-clustering/road-density"""
    snapshot = live_clustering_service.get_clustering_snapshot()
    return jsonify({
        "status": "success",
        "road_density": snapshot.get("road_density", {}),
    }), 200


@live_clustering_bp.route("/evaluation", methods=["GET"])
def get_evaluation():
    """GET /api/live-clustering/evaluation"""
    snapshot = live_clustering_service.get_clustering_snapshot()
    return jsonify({
        "status": "success",
        "evaluation": snapshot.get("evaluation", {}),
    }), 200


@live_clustering_bp.route("/traffic", methods=["GET", "POST"])
@live_clustering_bp.route("/area-snapshot", methods=["GET", "POST"])
def get_real_traffic():
    """GET /api/live-clustering/traffic — Real external traffic provider data."""
    if request.method == "POST":
        data = request.get_json() or {}
        lat = data.get("latitude")
        lon = data.get("longitude")
        radius_m = float(data.get("radius_meters", data.get("radius_m", 1000.0)))
        name = data.get("name", "Selected Area")
        if lat is not None and lon is not None:
            live_clustering_service.set_active_area(lat=float(lat), lon=float(lon), name=name, radius_m=radius_m)

    area = live_clustering_service.get_active_area()
    traffic_payload = live_clustering_service.get_real_traffic(fetch_fn=get_area_traffic)
    snapshot = live_clustering_service.get_clustering_snapshot()

    # Zone calculation for real traffic segments
    from .zone_clustering_service import zone_clustering_service
    segments = traffic_payload.get("segments", [])
    zones = zone_clustering_service.compute_zones(
        segments, area["latitude"], area["longitude"], area["radius_meters"]
    )

    t_status = traffic_payload.get("status", "UNAVAILABLE")
    if t_status == "UNAVAILABLE":
        top_status = "UNAVAILABLE"
    elif not segments:
        top_status = "NO_DATA"
    else:
        top_status = "success"

    return jsonify({
        "status": top_status,
        "success": True,
        "area": area,
        "traffic": traffic_payload,
        "zones": zones,
        "zone_data": zones.get("zones", []),
        "snapshot": snapshot,
    }), 200
