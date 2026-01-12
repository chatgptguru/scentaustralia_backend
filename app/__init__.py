"""
Flask Application Factory
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from loguru import logger
import os
import sys

from app.config import Config


def setup_logging():
    """Configure logging with loguru"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler
    logger.add(
        log_file,
        rotation="10 MB",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger


def create_app(config_class=Config):
    """Create and configure the Flask application"""
    
    # Setup logging
    setup_logging()
    logger.info("Starting Scent Australia Lead Generation AI Backend")
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Disable strict slashes to prevent redirects that break CORS preflight
    app.url_map.strict_slashes = False
    
    # Configure CORS - allow all origins for development
    # This will handle preflight OPTIONS requests automatically
    CORS(app, 
         resources={r"/api/*": {"origins": "*"}},
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         supports_credentials=False,
         automatic_options=True)
    
    # Create necessary directories
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Register blueprints
    from app.routes.leads import leads_bp
    from app.routes.apollo import apollo_bp
    from app.routes.export import export_bp
    from app.routes.health import health_bp
    
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(leads_bp, url_prefix='/api/leads')
    app.register_blueprint(apollo_bp, url_prefix='/api/apollo')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    
    logger.info("Application initialized successfully")
    
    return app
