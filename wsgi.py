#!/usr/bin/env python3
"""
Production WSGI entry point for WhatsApp OTP Service
Run with: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import app, initialize_service

# Configure production logging
if not app.debug:
    file_handler = RotatingFileHandler(
        'whatsapp_otp_service.log', 
        maxBytes=10485760, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('WhatsApp OTP Service startup')

# Initialize the service
initialize_service()

# WSGI application
application = app

if __name__ == "__main__":
    # For development
    app.run(host='0.0.0.0', port=5000, debug=False)
