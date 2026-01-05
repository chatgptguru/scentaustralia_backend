"""
Health Check Routes
"""

from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Scent Australia Lead Generation AI',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


@health_bp.route('/', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Scent Australia Lead Generation AI API',
        'version': '1.0.0',
        'description': 'AI-powered lead generation system for Scent Australia',
        'endpoints': {
            'health': '/api/health',
            'leads': '/api/leads',
            'scraper': '/api/scraper',
            'export': '/api/export'
        },
        'documentation': '/api/docs'
    })

