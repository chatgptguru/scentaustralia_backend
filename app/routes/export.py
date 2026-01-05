"""
Data Export Routes
"""

from flask import Blueprint, jsonify, request, send_file, current_app
from loguru import logger
from datetime import datetime
import os

from app.services.export_service import ExportService
from app.services.lead_manager import LeadManager

export_bp = Blueprint('export', __name__)

# Initialize services
export_service = ExportService()
lead_manager = LeadManager()


@export_bp.route('/excel', methods=['POST'])
def export_to_excel():
    """Export leads to Excel file"""
    try:
        data = request.get_json() or {}
        
        # Get filter parameters
        lead_ids = data.get('lead_ids')  # Specific leads to export
        status = data.get('status')
        priority = data.get('priority')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        # Get leads to export
        if lead_ids:
            leads = [lead_manager.get_lead_by_id(lid) for lid in lead_ids if lead_manager.get_lead_by_id(lid)]
        else:
            leads, _ = lead_manager.get_leads(
                status=status,
                priority=priority,
                page=1,
                per_page=current_app.config.get('MAX_EXPORT_ROWS', 10000)
            )
        
        if not leads:
            return jsonify({
                'success': False,
                'error': 'No leads found to export'
            }), 404
        
        # Generate Excel file
        filename = f"leads_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = export_service.export_to_excel(leads, filename)
        
        logger.info(f"Exported {len(leads)} leads to Excel: {filename}")
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'filepath': filepath,
                'total_exported': len(leads),
                'download_url': f'/api/export/download/{filename}'
            }
        })
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@export_bp.route('/csv', methods=['POST'])
def export_to_csv():
    """Export leads to CSV file"""
    try:
        data = request.get_json() or {}
        
        # Get filter parameters
        lead_ids = data.get('lead_ids')
        status = data.get('status')
        priority = data.get('priority')
        
        # Get leads to export
        if lead_ids:
            leads = [lead_manager.get_lead_by_id(lid) for lid in lead_ids if lead_manager.get_lead_by_id(lid)]
        else:
            leads, _ = lead_manager.get_leads(
                status=status,
                priority=priority,
                page=1,
                per_page=current_app.config.get('MAX_EXPORT_ROWS', 10000)
            )
        
        if not leads:
            return jsonify({
                'success': False,
                'error': 'No leads found to export'
            }), 404
        
        # Generate CSV file
        filename = f"leads_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = export_service.export_to_csv(leads, filename)
        
        logger.info(f"Exported {len(leads)} leads to CSV: {filename}")
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'filepath': filepath,
                'total_exported': len(leads),
                'download_url': f'/api/export/download/{filename}'
            }
        })
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@export_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download an exported file"""
    try:
        export_folder = current_app.config.get('EXPORT_FOLDER', 'exports')
        filepath = os.path.join(export_folder, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@export_bp.route('/files', methods=['GET'])
def list_export_files():
    """List all exported files"""
    try:
        export_folder = current_app.config.get('EXPORT_FOLDER', 'exports')
        
        if not os.path.exists(export_folder):
            return jsonify({
                'success': True,
                'data': {
                    'files': [],
                    'total': 0
                }
            })
        
        files = []
        for filename in os.listdir(export_folder):
            filepath = os.path.join(export_folder, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'download_url': f'/api/export/download/{filename}'
                })
        
        files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'total': len(files)
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing export files: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@export_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_export_file(filename):
    """Delete an exported file"""
    try:
        export_folder = current_app.config.get('EXPORT_FOLDER', 'exports')
        filepath = os.path.join(export_folder, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        os.remove(filepath)
        
        logger.info(f"Deleted export file: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

