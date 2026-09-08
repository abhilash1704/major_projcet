import logging
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from utils.response import ResponseHelper
from utils.errors import APIError

logger = logging.getLogger("routeflow.errors")

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return ResponseHelper.error(
            message=error.message,
            code=getattr(error, "code", "API_ERROR"),
            errors=getattr(error, "payload", None),
            status_code=error.status_code
        )

    @app.errorhandler(400)
    def bad_request(error):
        msg = error.description if isinstance(error, HTTPException) else "Bad request"
        return ResponseHelper.error(message=msg, code="BAD_REQUEST", status_code=400)

    @app.errorhandler(401)
    def unauthorized(error):
        msg = error.description if isinstance(error, HTTPException) else "Unauthorized access"
        return ResponseHelper.error(message=msg, code="UNAUTHORIZED", status_code=401)

    @app.errorhandler(403)
    def forbidden(error):
        msg = error.description if isinstance(error, HTTPException) else "Access forbidden"
        return ResponseHelper.error(message=msg, code="FORBIDDEN", status_code=403)

    @app.errorhandler(404)
    def not_found(error):
        msg = error.description if isinstance(error, HTTPException) else "Resource not found"
        return ResponseHelper.error(message=msg, code="NOT_FOUND", status_code=404)

    @app.errorhandler(408)
    def request_timeout(error):
        return ResponseHelper.error(message="Request timed out", code="REQUEST_TIMEOUT", status_code=408)

    @app.errorhandler(409)
    def conflict(error):
        msg = error.description if isinstance(error, HTTPException) else "Resource conflict"
        return ResponseHelper.error(message=msg, code="CONFLICT", status_code=409)

    @app.errorhandler(429)
    def too_many_requests(error):
        return ResponseHelper.error(message="Rate limit exceeded. Please slow down.", code="TOO_MANY_REQUESTS", status_code=429)

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error("[ServerError:500] %s", error)
        return ResponseHelper.error(message="Internal server error", code="INTERNAL_SERVER_ERROR", status_code=500)

    @app.errorhandler(TimeoutError)
    def handle_timeout(e):
        logger.warning("[TimeoutError] Operation timed out: %s", e)
        return ResponseHelper.error(message="Operation timed out", code="OPERATION_TIMEOUT", status_code=504)

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(e):
        logger.error("[DatabaseError] SQLAlchemy error: %s", e, exc_info=True)
        try:
            from database.db import db
            db.session.rollback()
        except Exception:
            pass
        return ResponseHelper.error(
            message="Database operation failed. Please retry.",
            code="DATABASE_ERROR",
            status_code=503
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return ResponseHelper.error(
                message=e.description,
                code=getattr(e, "name", "HTTP_EXCEPTION").upper().replace(" ", "_"),
                status_code=e.code
            )
        logger.exception("[UnhandledException] %s", e)
        return ResponseHelper.error(
            message="An unexpected error occurred.",
            code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
