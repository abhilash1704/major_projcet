from flask import jsonify

class ResponseHelper:
    @staticmethod
    def success(data=None, message="Success", status_code=200):
        response = {
            "status": "success",
            "message": message,
            "data": data
        }
        return jsonify(response), status_code

    @staticmethod
    def error(message="An error occurred", errors=None, status_code=400):
        response = {
            "status": "error",
            "message": message,
        }
        if errors:
            response["errors"] = errors
        return jsonify(response), status_code
