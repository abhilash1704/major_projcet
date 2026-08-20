from werkzeug.exceptions import HTTPException
from utils.response import ResponseHelper
from utils.errors import APIError

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return ResponseHelper.error(message=error.message, errors=error.payload, status_code=error.status_code)

    @app.errorhandler(404)
    def not_found(error):
        return ResponseHelper.error(message="Resource not found", status_code=404)

    @app.errorhandler(400)
    def bad_request(error):
        return ResponseHelper.error(message="Bad request", status_code=400)

    @app.errorhandler(401)
    def unauthorized(error):
        return ResponseHelper.error(message="Unauthorized access", status_code=401)

    @app.errorhandler(500)
    def internal_server_error(error):
        # In a real app, log the error here
        return ResponseHelper.error(message="Internal server error", status_code=500)
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return ResponseHelper.error(message=e.description, status_code=e.code)
        
        # Log unexpected errors here
        return ResponseHelper.error(message="An unexpected error occurred", status_code=500)
