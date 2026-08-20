"""
Routes Blueprint — /api/routes

Provides primary route endpoints:
    POST /api/routes/calculate — Calculate path using A* or Dijkstra
    POST /api/routes/compare   — Compare A* and Dijkstra execution performance
    GET  /api/routes/active    — Retrieve currently stored route
    DELETE /api/routes/active  — Clear active route
"""
import logging
from flask import Blueprint, jsonify, request
from app.services.routing_service import routing_service
import app.modules.vehicle_simulation.services.route_store as route_store

routes_bp = Blueprint("routes", __name__, url_prefix="/api/routes")
logger = logging.getLogger("routeflow.routes")


@routes_bp.route("/calculate", methods=["POST"])
def calculate_route():
    """
    POST /api/routes/calculate

    JSON body:
        {
            "source_node":        "7784026478",   (required)
            "destination_node":   "1032",          (required)
            "source_lat":         14.2445,         (optional)
            "source_lon":         75.8417,         (optional)
            "destination_lat":    15.3536,         (optional)
            "destination_lon":    76.8118,         (optional)
            "algorithm":          "astar" | "dijkstra" (optional, default: astar)
        }

    Returns:
        200 {
            "success": true,
            "status": "success",
            "route": {
                "status": "success",
                "algorithm": "astar" | "dijkstra",
                "source_node": "...",
                "destination_node": "...",
                "nodes": [...],
                "edges": [...],
                "distance_km": ...,
                "total_distance_km": ...,
                "travel_time_seconds": ...,
                "total_travel_time_seconds": ...,
                "eta_minutes": ...,
                "geometry": [...]
            }
        }
        400 — missing / invalid parameters, unsupported algorithm, or source == destination
        404 — node not found or no path exists
        503 — graph unavailable
    """
    data = request.get_json(silent=True) or {}

    src_raw = data.get("source_node") or data.get("source_node_id")
    tgt_raw = data.get("destination_node") or data.get("destination_node_id") or data.get("target_node")
    algorithm = data.get("algorithm", "astar")
    routing_mode = data.get("routing_mode") or data.get("mode") or "normal"

    src_lat = data.get("source_lat")
    src_lon = data.get("source_lon")
    dst_lat = data.get("destination_lat") or data.get("dest_lat")
    dst_lon = data.get("destination_lon") or data.get("dest_lon")

    try:
        route_result = routing_service.calculate_route(
            source_node=src_raw,
            destination_node=tgt_raw,
            algorithm=algorithm,
            source_lat=src_lat,
            source_lon=src_lon,
            destination_lat=dst_lat,
            destination_lon=dst_lon,
            weight="travel_time",
            routing_mode=routing_mode
        )
        
        # Persist to history if user is authenticated
        try:
            from app.modules.auth.security import extract_auth_token, verify_access_token
            from database.db import db
            from models.route_history import RouteHistory
            token = extract_auth_token()
            if token:
                payload = verify_access_token(token)
                if payload and payload.get('sub'):
                    user_id = payload.get('sub')
                    history_entry = RouteHistory(
                        user_id=user_id,
                        source_name=data.get("source_name") or "Unknown Location",
                        source_latitude=src_lat,
                        source_longitude=src_lon,
                        destination_name=data.get("destination_name") or "Unknown Location",
                        destination_latitude=dst_lat,
                        destination_longitude=dst_lon,
                        distance_km=route_result.get("distance_km"),
                        eta_minutes=route_result.get("eta_minutes"),
                        algorithm=route_result.get("algorithm"),
                        routing_mode=route_result.get("routing_mode"),
                        traffic_level=route_result.get("traffic_level"),
                        traffic_penalty=route_result.get("traffic_cost")
                    )
                    db.session.add(history_entry)
                    db.session.commit()
        except Exception as e:
            logger.warning("Failed to persist route history: %s", e)
            try:
                from database.db import db
                db.session.rollback()
            except:
                pass

        return jsonify({
            "success": True,
            "status": "success",
            "route": route_result
        }), 200

    except TimeoutError as exc:
        return jsonify({
            "success": False,
            "status": "error",
            "error": "ROUTE_TIMEOUT",
            "message": str(exc),
        }), 504

    except ValueError as exc:
        msg = str(exc)
        if "Unsupported routing algorithm" in msg:
            return jsonify({"success": False, "status": "error", "error": "Unsupported routing algorithm"}), 400
        if "is not present in the routing graph" in msg or "not found" in msg.lower():
            return jsonify({"success": False, "status": "error", "error": msg}), 404
        if "no valid road path" in msg.lower() or "no path" in msg.lower():
            return jsonify({"success": False, "status": "error", "error": msg}), 404
        return jsonify({"success": False, "status": "error", "error": msg}), 400

    except RuntimeError as exc:
        return jsonify({"success": False, "status": "error", "error": str(exc)}), 503

    except Exception as exc:
        logger.exception("Unexpected error during route calculation")
        return jsonify({
            "success": False,
            "status": "error",
            "error": "Internal server error during route calculation"
        }), 500


@routes_bp.route("/compare", methods=["POST"])
def compare_algorithms():
    """
    POST /api/routes/compare

    Runs both A* and Dijkstra on the identical graph instance with the same source
    and destination to measure and compare execution times and path metrics.
    """
    data = request.get_json(silent=True) or {}

    src_raw = data.get("source_node") or data.get("source_node_id")
    tgt_raw = data.get("destination_node") or data.get("destination_node_id") or data.get("target_node")
    routing_mode = data.get("routing_mode") or data.get("mode") or "normal"

    src_lat = data.get("source_lat")
    src_lon = data.get("source_lon")
    dst_lat = data.get("destination_lat") or data.get("dest_lat")
    dst_lon = data.get("destination_lon") or data.get("dest_lon")

    try:
        res = routing_service.compare_algorithms(
            source_node=src_raw,
            destination_node=tgt_raw,
            source_lat=src_lat,
            source_lon=src_lon,
            destination_lat=dst_lat,
            destination_lon=dst_lon,
            weight="travel_time",
            routing_mode=routing_mode
        )
        return jsonify(res), 200
    except TimeoutError as exc:
        return jsonify({
            "success": False,
            "status": "error",
            "error": "ROUTE_TIMEOUT",
            "message": str(exc),
        }), 504

    except ValueError as exc:
        msg = str(exc)
        if "is not present in the routing graph" in msg or "not found" in msg.lower():
            return jsonify({"success": False, "status": "error", "error": msg}), 404
        if "no valid road path" in msg.lower() or "no path" in msg.lower():
            return jsonify({"success": False, "status": "error", "error": msg}), 404
        return jsonify({"success": False, "status": "error", "error": msg}), 400
    except RuntimeError as exc:
        return jsonify({"success": False, "status": "error", "error": str(exc)}), 503
    except Exception as exc:
        logger.exception("Unexpected error during algorithm comparison")
        return jsonify({
            "success": False,
            "status": "error",
            "error": "Internal server error during algorithm comparison"
        }), 500


@routes_bp.route("/active", methods=["GET"])
def get_active_route():
    """GET /api/routes/active — return the currently stored route summary and rerouting recommendations."""
    r = route_store.get_route()
    if r is None:
        return jsonify({
            "success": False,
            "error": "No active route",
            "reroute_recommendation": {"recommended": False, "reason": "No active route"}
        }), 404
        
    # Sprint 11 Dynamic Rerouting Evaluation
    try:
        from app.services.routing_service import routing_service
        rec = routing_service.evaluate_reroute()
    except Exception as exc:
        logger.exception("Failed to evaluate reroute")
        rec = {"recommended": False, "reason": "Internal evaluation error"}

    return jsonify({
        "success": True,
        "route": r,
        "algorithm": route_store.get_algorithm(),
        "routing_mode": route_store.get_routing_mode(),
        "route_cost": route_store.get_current_cost(),
        "original_cost": route_store.get_original_cost(),
        "last_reroute_time": route_store.get_last_reroute_time(),
        "last_evaluation_time": route_store.get_last_evaluation_time(),
        "previous_route_cost": route_store.get_previous_route_cost(),
        "reroute_reason": route_store.get_reroute_reason(),
        "reroute_status": route_store.get_reroute_status(),
        "reroute_recommendation": rec
    })


@routes_bp.route("/active", methods=["POST"])
def set_active_route():
    """POST /api/routes/active — sets the active route explicitly (e.g. user accepts reroute or toggles algorithm)."""
    data = request.get_json()
    if not data or "route" not in data:
        return jsonify({"success": False, "error": "Invalid request payload"}), 400
        
    import time
    route_obj = data["route"]
    algorithm = data.get("algorithm", "astar")
    routing_mode = data.get("routing_mode", "normal")
    reason = data.get("reason", "User updated route")
    
    route_store.set_route(route_obj, algorithm=algorithm, routing_mode=routing_mode)
    route_store.set_last_reroute_time(time.time())
    route_store.set_reroute_status("rerouted")
    route_store.set_reroute_reason(reason)
    
    return jsonify({"success": True, "message": "Active route updated successfully"})


@routes_bp.route("/active/reject", methods=["POST"])
def reject_reroute():
    """POST /api/routes/active/reject — records that user rejected a reroute recommendation, starting cooldown."""
    import time
    route_store.set_last_reroute_time(time.time())
    route_store.set_reroute_status("stable")
    route_store.set_reroute_reason("User rejected alternative route")
    return jsonify({"success": True, "message": "Reroute rejected, cooldown restarted"})


@routes_bp.route("/active", methods=["DELETE"])
def clear_active_route():
    """DELETE /api/routes/active — clear the stored route."""
    route_store.clear_route()
    return jsonify({"success": True, "message": "Active route cleared"})


@routes_bp.route("/alternatives", methods=["POST"])
def get_alternative_routes():
    """
    POST /api/routes/alternatives

    Triggered when HIGH traffic is detected on active route.
    Generates 2-3 algorithmically diverse alternative routes using A* and Dijkstra.

    JSON Payload:
    {
        "source": "...",
        "destination": "...",
        "current_route": {...},
        "traffic_level": "HIGH",
        "max_alternatives": 3,
        "request_id": "..."
    }
    """
    data = request.get_json(silent=True) or {}

    source = data.get("source") or data.get("source_node") or data.get("source_node_id")
    destination = data.get("destination") or data.get("destination_node") or data.get("target_node")
    current_route = data.get("current_route") or data.get("route")
    traffic_level = data.get("traffic_level", "HIGH")
    max_alternatives = int(data.get("max_alternatives", 2))
    request_id = data.get("request_id") or data.get("alternative_request_id")

    if not source or not destination:
        # Try fetching from route_store if available
        active_r = route_store.get_route()
        if active_r:
            if not source:
                source = active_r.get("source_node_id")
            if not destination:
                destination = active_r.get("target_node_id")
            if not current_route:
                current_route = active_r

    if not source or not destination:
        return jsonify({
            "status": "error",
            "trigger": "MISSING_PARAMETERS",
            "message": "Both source and destination are required.",
            "current_route": current_route or {},
            "alternatives": []
        }), 400

    try:
        from app.modules.routing.services.alternative_route_service import alternative_route_service
        res = alternative_route_service.generate_alternative_routes(
            source_node=source,
            destination_node=destination,
            current_route=current_route,
            traffic_level=traffic_level,
            max_alternatives=max_alternatives,
            request_id=request_id
        )
        return jsonify(res), 200

    except Exception as exc:
        logger.exception("Error generating alternative routes: %s", exc)
        return jsonify({
            "status": "error",
            "trigger": "SERVER_ERROR",
            "message": str(exc),
            "current_route": current_route or {},
            "alternatives": []
        }), 500

