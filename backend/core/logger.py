import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(app):
    if not app.debug and not app.testing:
        # File Logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler('logs/routeflow.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('RouteFlow API startup')
    else:
        # Console Logging
        logging.basicConfig(level=logging.DEBUG)
