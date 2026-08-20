"""
Vehicle Simulation Routes — Sprint 4.1 / 4.2 / 4.3

Flask Blueprint providing the full vehicle REST API:

    GET    /api/vehicles                  — list all vehicles
    POST   /api/vehicles                  — create a single vehicle
    GET    /api/vehicles/<vehicle_id>     — get a vehicle by ID
    PUT    /api/vehicles/<vehicle_id>     — update a vehicle
    DELETE /api/vehicles/<vehicle_id>     — delete a vehicle
    POST   /api/vehicles/generate         — generate vehicles on road edges
    DELETE /api/vehicles/simulation       — clear all simulated vehicles
    POST   /api/vehicles/simulation/update— advance simulation by delta_seconds
    GET    /api/vehicles/snapshot         — lightweight read of all vehicle positions

Business logic is delegated to service/generator/movement layers.
This file only handles HTTP parsing and response formatting.
"""
from flask import Blueprint, jsonify, request
from .services.vehicle_service import vehicle_service
from .services.vehicle_generator import vehicle_generator
from .services.vehicle_movement_service import vehicle_movement_service
from .schemas.vehicle_schema import VehicleSchema
from .constants import MODULE_NAME, MODULE_VERSION, MAX_GENERATION_COUNT, MAX_TICKS_PER_REQUEST
import app.modules.vehicle_simulation.services.route_store as route_store

vehicle_simulation_bp = Blueprint(
    "vehicle_simulation", __name__, url_prefix="/api/vehicles"
)


from .services.simulation_store import simulation_store

# ── Health / module info ───────────────────────────────────────────────────────

@vehicle_simulation_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "module": MODULE_NAME, "version": MODULE_VERSION})


# ── CRUD ───────────────────────────────────────────────────────────────────────

@vehicle_simulation_bp.route("", methods=["GET"])
def list_vehicles():
    """GET /api/vehicles — return all vehicle records."""
    vehicles = vehicle_service.get_all_vehicles()
    return jsonify({
        "vehicles": VehicleSchema.dump_many(vehicles),
        "count":    len(vehicles),
    })


@vehicle_simulation_bp.route("", methods=["POST"])
def create_vehicle():
    """POST /api/vehicles — create a single vehicle from JSON body."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Request body must be valid JSON."}), 400

    try:
        vehicle = vehicle_service.create_vehicle(data)
        return jsonify({
            "status":  "success",
            "vehicle": VehicleSchema.dump(vehicle),
        }), 201
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@vehicle_simulation_bp.route("/<vehicle_id>", methods=["GET"])
def get_vehicle(vehicle_id):
    """GET /api/vehicles/<vehicle_id> — retrieve a single vehicle."""
    vehicle = vehicle_service.get_vehicle(vehicle_id)
    if vehicle is None:
        return jsonify({
            "status":  "error",
            "message": f"Vehicle '{vehicle_id}' not found.",
        }), 404

    return jsonify({"status": "success", "vehicle": VehicleSchema.dump(vehicle)})


@vehicle_simulation_bp.route("/<vehicle_id>", methods=["PUT"])
def update_vehicle(vehicle_id):
    """PUT /api/vehicles/<vehicle_id> — update vehicle state."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Request body must be valid JSON."}), 400

    try:
        vehicle = vehicle_service.update_vehicle_position(vehicle_id, data)
        return jsonify({
            "status":  "success",
            "vehicle": VehicleSchema.dump(vehicle),
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@vehicle_simulation_bp.route("/<vehicle_id>", methods=["DELETE"])
def delete_vehicle(vehicle_id):
    """DELETE /api/vehicles/<vehicle_id> — delete a vehicle record."""
    try:
        deleted = vehicle_service.delete_vehicle(vehicle_id)
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

    if not deleted:
        return jsonify({
            "status":  "error",
            "message": f"Vehicle '{vehicle_id}' not found.",
        }), 404

    return jsonify({"status": "success", "message": f"Vehicle '{vehicle_id}' deleted."})


# ── Generation ─────────────────────────────────────────────────────────────────

@vehicle_simulation_bp.route("/generate", methods=["POST"])
def generate_vehicles():
    """
    POST /api/vehicles/generate

    JSON body:
        {
            "count":     100,           (required)
            "seed":      42,            (optional — for reproducibility)
            "cache_key": "my_graph"     (optional — road graph cache key)
        }
    """
    data = request.get_json(silent=True) or {}

    raw_count = data.get("count")
    if raw_count is None:
        return jsonify({"status": "error", "message": "'count' is required in the request body."}), 400

    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": f"'count' must be a numeric integer, got: {raw_count!r}"}), 400

    if count <= 0:
        return jsonify({"status": "error", "message": f"'count' must be a positive integer, got {count}."}), 400

    if count > MAX_GENERATION_COUNT:
        return jsonify({
            "status":  "error",
            "message": f"'count' {count} exceeds the maximum allowed ({MAX_GENERATION_COUNT})."
        }), 400

    seed      = data.get("seed")
    cache_key = data.get("cache_key")
    route_nodes = data.get("route_nodes")
    
    # 1. Stop previous simulation & reset memory
    new_sim_id = simulation_store.reset_session()
    simulation_store.set_status("GENERATING")

    # Wipe DB vehicles for the new simulation session (we clear all for simplicity, or we can clear stale ones)
    try:
        vehicle_service.delete_all_vehicles()
    except Exception:
        pass

    try:
        result = vehicle_generator.generate(
            count=count,
            seed=int(seed) if seed is not None else None,
            cache_key=cache_key,
            route_nodes=route_nodes,
            simulation_id=new_sim_id,
        )
        # Add simulation_id to result vehicles and memory
        for v in result.get("vehicles", []):
            v["simulation_id"] = new_sim_id
            
        simulation_store.initialize_vehicles(new_sim_id, result.get("vehicles", []))
        simulation_store.set_status("READY")
        
        result["simulation_id"] = new_sim_id
        result["status"] = "READY"
        
        return jsonify({"status": "success", **result}), 201
    except Exception as exc:
        simulation_store.set_status("ERROR")
        return jsonify({"status": "error", "message": str(exc)}), 500


# ── Lifecycle Endpoints ────────────────────────────────────────────────────────

@vehicle_simulation_bp.route("/simulation/start", methods=["POST"])
def start_simulation():
    if simulation_store.status not in ["READY", "PAUSED", "IDLE"]:
        return jsonify({"status": "error", "message": f"Cannot start from status {simulation_store.status}"}), 400
    if simulation_store.get_vehicle_count() == 0:
        return jsonify({"status": "error", "message": "No vehicles generated."}), 400
    
    simulation_store.set_status("RUNNING")
    return jsonify({"status": "success", "simulation_status": "RUNNING", "simulation_id": simulation_store.simulation_id})

@vehicle_simulation_bp.route("/simulation/pause", methods=["POST"])
def pause_simulation():
    if simulation_store.status == "RUNNING":
        simulation_store.set_status("PAUSED")
    return jsonify({"status": "success", "simulation_status": simulation_store.status, "simulation_id": simulation_store.simulation_id})

@vehicle_simulation_bp.route("/simulation/resume", methods=["POST"])
def resume_simulation():
    if simulation_store.status == "PAUSED":
        simulation_store.set_status("RUNNING")
    return jsonify({"status": "success", "simulation_status": simulation_store.status, "simulation_id": simulation_store.simulation_id})

@vehicle_simulation_bp.route("/simulation", methods=["DELETE"])
def reset_simulation():
    """
    DELETE /api/vehicles/simulation
    """
    try:
        # Reset memory state entirely
        simulation_store.reset_session()
        # Wipe DB
        deleted_count = vehicle_service.delete_all_vehicles()
        route_store.clear_route()
        return jsonify({
            "status":  "success",
            "message": f"Simulation cleared. {deleted_count} vehicle(s) removed.",
            "deleted": deleted_count,
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# ── Movement ───────────────────────────────────────────────────────────────────

@vehicle_simulation_bp.route("/simulation/update", methods=["POST"])
def simulation_update():
    """
    POST /api/vehicles/simulation/update
    """
    if simulation_store.status != "RUNNING":
        # Vehicle movement must occur ONLY when simulation status is RUNNING.
        # READY must not advance vehicle positions. Return current state without advancing.
        return jsonify({"status": "success", **simulation_store.get_snapshot()})
        
    data = request.get_json(silent=True) or {}

    if "delta_seconds" not in data:
        return jsonify({"status": "error", "message": "'delta_seconds' is required in the request body."}), 400

    raw_delta = data.get("delta_seconds")
    try:
        delta_seconds = float(raw_delta)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": f"'delta_seconds' must be a number, got {raw_delta!r}"}), 400

    if delta_seconds <= 0 or delta_seconds > 3600:
        return jsonify({"status": "error", "message": "delta_seconds must be > 0 and <= 3600"}), 400

    seed      = data.get("seed")
    cache_key = data.get("cache_key")

    try:
        result = vehicle_movement_service.update_vehicle_positions(
            delta_seconds=delta_seconds,
            cache_key=cache_key,
            seed=int(seed) if seed is not None else None,
        )
        return jsonify({"status": "success", **result})
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503


@vehicle_simulation_bp.route("/snapshot", methods=["GET"])
def vehicle_snapshot():
    """
    GET /api/vehicles/snapshot
    """
    try:
        snapshot = simulation_store.get_snapshot()
        return jsonify({"status": "success", **snapshot})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

