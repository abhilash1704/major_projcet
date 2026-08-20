from flask import Blueprint, jsonify, request
from .constants import MODULE_NAME, MODULE_VERSION, OSM_PROVIDER_DEFAULT_URL, MAX_GRAPH_NODES, DEFAULT_GEO_BOUNDS
from .services import osm_service, graph_service, node_service, routing_service

road_network_bp = Blueprint('road_network', __name__, url_prefix='/api/road-network')

@road_network_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for the Road Network Engine module.
    """
    return jsonify({
        "status": "ok",
        "module": "road-network"
    })

@road_network_bp.route('/ingest', methods=['POST', 'GET'])
def ingest_road_network():
    """
    Triggers OpenStreetMap data fetching, graph construction via NetworkX,
    topology validation, and disk caching.
    """
    data = request.get_json(silent=True) or {}
    bbox = data.get('bbox')
    force_refresh = data.get('force_refresh', False)
    cache_key = data.get('cache_key', 'bangalore_default')

    result = graph_service.ingest_osm_and_build(
        bbox=bbox,
        force_refresh=force_refresh,
        cache_key=cache_key
    )

    return jsonify({
        "status": "success",
        "message": "Road graph ingested, validated, and ready for routing.",
        "data": {
            "ingestion_status": result.get("status"),
            "source": result.get("source", "cache"),
            "stats": result.get("stats")
        }
    })

@road_network_bp.route('/summary', methods=['GET'])
def get_graph_summary():
    """
    Returns summary statistics of the currently loaded road graph.
    """
    stats = graph_service.get_graph_stats()
    return jsonify({
        "status": "ok",
        "module": MODULE_NAME,
        "summary": stats
    })


@road_network_bp.route('/diagnostics', methods=['GET'])
def get_network_diagnostics():
    """
    Returns a comprehensive diagnostic report of the active Bengaluru road network.

    Reports:
        - Road Network name
        - Total Nodes & Edges
        - Latitude/Longitude min → max
        - Connected Components count & largest component size
        - Spatial Index status
        - Graph status
    """
    try:
        diag = graph_service.get_network_diagnostics()
        return jsonify({
            "status": "ok",
            "diagnostics": diag
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Diagnostics unavailable: {exc}"
        }), 500


@road_network_bp.route('/coverage-test', methods=['GET'])
def get_coverage_test():
    """
    Runs a 9-point Bengaluru grid test to verify road-node coverage.

    Tests:
        North, South, East, West, Central, North-East, North-West, South-East, South-West

    Returns SUCCESS or OUTSIDE NETWORK for each grid point.
    """
    try:
        result = graph_service.get_coverage_test()
        return jsonify({
            "status": "ok",
            "coverage": result
        })
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Coverage test unavailable: {exc}"
        }), 500

@road_network_bp.route('/nodes/nearest', methods=['GET'])
def get_nearest_node():
    """
    Finds nearest graph node to specified lat and lon.
    Query params: ?lat=12.9716&lon=77.5946
    """
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is None or lon is None:
        return jsonify({
            "status": "error",
            "success": False,
            "found": False,
            "reason": "INVALID_COORDINATES",
            "message": "Location could not be found. Missing required query parameters: 'lat' and 'lon'"
        }), 400

    try:
        nearest = node_service.find_nearest_node(lat, lon)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "success": False,
            "found": False,
            "reason": "SERVICE_UNAVAILABLE",
            "message": "Road network service is temporarily unavailable.",
            "details": str(exc)
        }), 500

    if not nearest:
        return jsonify({
            "status": "error",
            "success": False,
            "found": False,
            "reason": "SERVICE_UNAVAILABLE",
            "message": "Road network service is temporarily unavailable."
        }), 500

    if not nearest.get("success", True):
        reason = nearest.get("reason", "OUTSIDE_NETWORK_COVERAGE")
        status_code = 400 if reason in ["OUTSIDE_NETWORK_COVERAGE", "INVALID_COORDINATES"] else 500
        return jsonify({
            "status": "error",
            "success": False,
            "found": False,
            "reason": reason,
            "error": nearest.get("error", "LOCATION_OUTSIDE_ROAD_NETWORK"),
            "message": nearest.get("message", "Location is outside the available road network."),
            "max_search_radius_km": nearest.get("max_search_radius_km", 20),
            "distance_km": nearest.get("distance_km")
        }), status_code

    return jsonify({
        "status": "success",
        "success": True,
        "nearest_node": nearest
    })

@road_network_bp.route('/route', methods=['GET', 'POST'])
def calculate_route():
    """
    Calculates optimal route between source and target using Dijkstra or A* search algorithms.
    Supports either node IDs (source_node, target_node) or raw coordinates (source_lat, source_lon, target_lat, target_lon).
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        src_node = data.get('source_node') or data.get('source_node_id')
        tgt_node = data.get('target_node') or data.get('target_node_id')
        src_lat = data.get('source_lat')
        src_lon = data.get('source_lon')
        tgt_lat = data.get('target_lat')
        tgt_lon = data.get('target_lon')
        algorithm = data.get('algorithm', 'dijkstra')
        weight = data.get('weight', 'travel_time')
        routing_mode = data.get('routing_mode') or data.get('mode') or 'normal'
    else:
        src_node = request.args.get('source_node')
        tgt_node = request.args.get('target_node')
        src_lat = request.args.get('source_lat', type=float)
        src_lon = request.args.get('source_lon', type=float)
        tgt_lat = request.args.get('target_lat', type=float)
        tgt_lon = request.args.get('target_lon', type=float)
        algorithm = request.args.get('algorithm', 'dijkstra')
        weight = request.args.get('weight', 'travel_time')
        routing_mode = request.args.get('routing_mode') or request.args.get('mode') or 'normal'

    try:
        if src_node and tgt_node:
            route_data = routing_service.calculate_route(
                source_node_id=str(src_node),
                target_node_id=str(tgt_node),
                algorithm=algorithm,
                weight=weight
            )
        elif src_lat is not None and src_lon is not None and tgt_lat is not None and tgt_lon is not None:
            # Resolve coordinates to road nodes, then route
            s_res = node_service.find_nearest_node(src_lat, src_lon)
            d_res = node_service.find_nearest_node(tgt_lat, tgt_lon)
            if not s_res or not s_res.get("success"):
                return jsonify({
                    "status": "error",
                    "message": "Source location is outside the available road network."
                }), 400
            if not d_res or not d_res.get("success"):
                return jsonify({
                    "status": "error",
                    "message": "Destination location is outside the available road network."
                }), 400
            route_data = routing_service.calculate_route(
                source_node_id=str(s_res["node_id"]),
                target_node_id=str(d_res["node_id"]),
                algorithm=algorithm,
                weight=weight
            )
        else:
            return jsonify({
                "status": "error",
                "message": "Missing routing parameters. Provide either (source_node, target_node) or (source_lat, source_lon, target_lat, target_lon)."
            }), 400

        return jsonify({
            "status": "success",
            "route": route_data
        })
    except ValueError as ve:
        return jsonify({
            "status": "error",
            "message": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server routing error: {str(e)}"
        }), 500

@road_network_bp.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "ok",
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "services": {
            "osm": osm_service.health_check(),
            "graph": graph_service.get_graph_stats()
        }
    })

@road_network_bp.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        "osm_provider": OSM_PROVIDER_DEFAULT_URL,
        "max_graph_nodes": MAX_GRAPH_NODES,
        "default_bounds": DEFAULT_GEO_BOUNDS
    })