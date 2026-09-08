from flask import jsonify, g, has_request_context

class ResponseHelper:
    @staticmethod
    def _get_request_id():
        if has_request_context():
            return getattr(g, "request_id", None)
        return None

    @staticmethod
    def success(data=None, message="Success", status_code=200, request_id=None):
        req_id = request_id or ResponseHelper._get_request_id()
        response = {
            "success": True,
            "status": "success",
            "message": message,
            "data": data,
        }
        if req_id:
            response["request_id"] = req_id
        return jsonify(response), status_code

    @staticmethod
    def error(message="An error occurred", code="API_ERROR", errors=None, status_code=400, request_id=None):
        req_id = request_id or ResponseHelper._get_request_id()
        err_obj = {
            "code": code,
            "message": message,
        }
        if errors:
            err_obj["details"] = errors
        response = {
            "success": False,
            "status": "error",
            "message": message,
            "error": err_obj,
        }
        if errors:
            response["errors"] = errors
        if req_id:
            response["request_id"] = req_id
        return jsonify(response), status_code
