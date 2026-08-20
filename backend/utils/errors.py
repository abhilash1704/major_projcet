class APIError(Exception):
    """Base API Error class"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class ValidationError(APIError):
    def __init__(self, message="Validation Error", payload=None):
        super().__init__(message, status_code=400, payload=payload)

class UnauthorizedError(APIError):
    def __init__(self, message="Unauthorized"):
        super().__init__(message, status_code=401)
