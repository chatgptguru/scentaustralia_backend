"""
Lead Management Routes
"""

from flask import Blueprint, jsonify, request
from loguru import logger
from datetime import datetime
import uuid

from app.services.lead_manager import LeadManager
from app.services.ai_analyzer import AILeadAnalyzer
from app.models.lead import Lead, LeadStatus, LeadPriority

leads_bp = Blueprint('leads', __name__)

# Initialize services
lead_manager = LeadManager()
ai_analyzer = AILeadAnalyzer()


@leads_bp.route('/', methods=['GET'])
def get_leads():
    """Get all leads with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        industry = request.args.get('industry')
        location = request.args.get('location')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Get leads from manager
        leads, total = lead_manager.get_leads(
            status=status,
            priority=priority,
            industry=industry,
            location=location,
            search=search,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'data': {
                'leads': [lead.to_dict() for lead in leads],
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/<lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a single lead by ID"""
    try:
        lead = lead_manager.get_lead_by_id(lead_id)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': 'Lead not found'
            }), 404
            
        return jsonify({
            'success': True,
            'data': lead.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error fetching lead {lead_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/', methods=['POST'])
def create_lead():
    """Create a new lead manually"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['company_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create lead
        lead = lead_manager.create_lead(data)
        
        # Optionally analyze with AI
        if data.get('analyze', False):
            analysis = ai_analyzer.analyze_lead(lead)
            lead.ai_analysis = analysis
            lead_manager.update_lead(lead.id, {'ai_analysis': analysis})
        
        logger.info(f"Created new lead: {lead.company_name}")
        
        return jsonify({
            'success': True,
            'data': lead.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating lead: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/<lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """Update an existing lead"""
    try:
        data = request.get_json()
        
        lead = lead_manager.update_lead(lead_id, data)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': 'Lead not found'
            }), 404
            
        logger.info(f"Updated lead: {lead_id}")
        
        return jsonify({
            'success': True,
            'data': lead.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/<lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    """Delete a lead"""
    try:
        success = lead_manager.delete_lead(lead_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Lead not found'
            }), 404
            
        logger.info(f"Deleted lead: {lead_id}")
        
        return jsonify({
            'success': True,
            'message': 'Lead deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/<lead_id>/analyze', methods=['POST'])
def analyze_lead(lead_id):
    """Analyze a lead using AI"""
    try:
        lead = lead_manager.get_lead_by_id(lead_id)
        
        if not lead:
            return jsonify({
                'success': False,
                'error': 'Lead not found'
            }), 404
        
        # Perform AI analysis
        analysis = ai_analyzer.analyze_lead(lead)
        
        # Update lead with analysis
        lead_manager.update_lead(lead_id, {
            'ai_analysis': analysis,
            'score': analysis.get('score', lead.score)
        })
        
        logger.info(f"AI analysis completed for lead: {lead_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'lead_id': lead_id,
                'analysis': analysis
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing lead {lead_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/bulk-analyze', methods=['POST'])
def bulk_analyze_leads():
    """Analyze multiple leads using AI"""
    try:
        data = request.get_json()
        lead_ids = data.get('lead_ids', [])
        
        if not lead_ids:
            return jsonify({
                'success': False,
                'error': 'No lead IDs provided'
            }), 400
        
        results = []
        for lead_id in lead_ids:
            lead = lead_manager.get_lead_by_id(lead_id)
            if lead:
                analysis = ai_analyzer.analyze_lead(lead)
                lead_manager.update_lead(lead_id, {
                    'ai_analysis': analysis,
                    'score': analysis.get('score', lead.score)
                })
                results.append({
                    'lead_id': lead_id,
                    'status': 'success',
                    'analysis': analysis
                })
            else:
                results.append({
                    'lead_id': lead_id,
                    'status': 'not_found'
                })
        
        logger.info(f"Bulk AI analysis completed for {len(lead_ids)} leads")
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'total_processed': len(results)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in bulk analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@leads_bp.route('/stats', methods=['GET'])
def get_lead_stats():
    """Get lead statistics"""
    try:
        stats = lead_manager.get_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching lead stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

