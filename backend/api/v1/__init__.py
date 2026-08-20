from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import endpoints to register them with the blueprint
from . import endpoints
