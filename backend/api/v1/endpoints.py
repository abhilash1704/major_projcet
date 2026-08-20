from . import api_v1
from utils.response import ResponseHelper
from utils.constants import Constants

@api_v1.route('/status', methods=['GET'])
def get_status():
    return ResponseHelper.success(data={"status": "online"}, message="API is running")

@api_v1.route('/health', methods=['GET'])
def get_health():
    return ResponseHelper.success(data={"database": "connected"}, message="System is healthy")

@api_v1.route('/version', methods=['GET'])
def get_version():
    return ResponseHelper.success(data={"version": Constants.VERSION})

@api_v1.route('/system/info', methods=['GET'])
def get_system_info():
    return ResponseHelper.success(data={
        "app_name": Constants.APP_NAME,
        "environment": "development"
    })
