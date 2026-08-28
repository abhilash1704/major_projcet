import logging
from flask import Blueprint, jsonify, request
from database.db import db
from models.route_history import RouteHistory

history_bp = Blueprint("history", __name__, url_prefix="/api/history")
logger = logging.getLogger("routeflow.history")

@history_bp.route("", methods=["GET"])
def get_history():
    """GET /api/history — fetch paginated history records for the guest user."""
    try:
        user_id = "guest_user"
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        
        algorithm = request.args.get("algorithm")
        routing_mode = request.args.get("routing_mode")
        traffic_level = request.args.get("traffic_level")
        search = request.args.get("search")

        query = db.session.query(RouteHistory).filter(
            RouteHistory.user_id == user_id,
            RouteHistory.is_deleted == False
        )

        if algorithm and algorithm.lower() != "all":
            query = query.filter(RouteHistory.algorithm.ilike(f"%{algorithm}%"))
        
        if routing_mode and routing_mode.lower() != "all":
            query = query.filter(RouteHistory.routing_mode.ilike(f"%{routing_mode}%"))
            
        if traffic_level and traffic_level.lower() != "all":
            query = query.filter(RouteHistory.traffic_level.ilike(f"%{traffic_level}%"))
            
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    RouteHistory.source_name.ilike(search_term),
                    RouteHistory.destination_name.ilike(search_term)
                )
            )

        query = query.order_by(RouteHistory.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        
        items = [item.to_dict() for item in pagination.items]
        
        return jsonify({
            "success": True,
            "items": items,
            "page": pagination.page,
            "limit": pagination.per_page,
            "total": pagination.total,
            "has_next": pagination.has_next
        }), 200
    except Exception as exc:
        logger.exception("Failed to fetch route history")
        return jsonify({
            "success": False,
            "error": "Failed to fetch history"
        }), 500


@history_bp.route("/<id>", methods=["DELETE"])
def delete_history(id):
    """DELETE /api/history/<id> — soft delete a history record."""
    try:
        record = db.session.query(RouteHistory).filter_by(id=id, is_deleted=False).first()
        
        if not record:
            return jsonify({"success": False, "error": "Record not found"}), 404
            
        if record.user_id != "guest_user":
            return jsonify({"success": False, "error": "Record not found"}), 404

        record.soft_delete()
        db.session.commit()
        
        return jsonify({"success": True, "message": "History record deleted"}), 200
    except Exception as exc:
        logger.exception("Failed to delete route history")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Failed to delete history"
        }), 500
