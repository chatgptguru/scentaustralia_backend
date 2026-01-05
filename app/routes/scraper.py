"""
Web Scraper Routes
"""

from flask import Blueprint, jsonify, request, current_app
from loguru import logger
from datetime import datetime
import threading

from app.services.scraper_service import ScraperService
from app.services.lead_manager import LeadManager
from app.services.ai_analyzer import AILeadAnalyzer

scraper_bp = Blueprint('scraper', __name__)

# Initialize services
scraper_service = ScraperService()
lead_manager = LeadManager()
ai_analyzer = AILeadAnalyzer()

# Store for tracking scraping jobs
scraping_jobs = {}


@scraper_bp.route('/start', methods=['POST'])
def start_scraping():
    """Start a new scraping job"""
    try:
        data = request.get_json() or {}
        
        # Get scraping parameters
        keywords = data.get('keywords', current_app.config.get('TARGET_INDUSTRIES', []))
        locations = data.get('locations', current_app.config.get('TARGET_LOCATIONS', []))
        max_leads = data.get('max_leads', current_app.config.get('MAX_LEADS_PER_RUN', 100))
        sources = data.get('sources', ['google_search', 'yellow_pages'])
        analyze_with_ai = data.get('analyze_with_ai', True)
        
        # Generate job ID
        job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize job status
        scraping_jobs[job_id] = {
            'id': job_id,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'total_leads': 0,
            'processed_leads': 0,
            'errors': [],
            'parameters': {
                'keywords': keywords,
                'locations': locations,
                'max_leads': max_leads,
                'sources': sources,
                'analyze_with_ai': analyze_with_ai
            }
        }
        
        # Start scraping in background thread
        thread = threading.Thread(
            target=run_scraping_job,
            args=(job_id, keywords, locations, max_leads, sources, analyze_with_ai)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started scraping job: {job_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'running',
                'message': 'Scraping job started successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting scraping job: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_scraping_job(job_id, keywords, locations, max_leads, sources, analyze_with_ai):
    """Execute scraping job in background"""
    try:
        logger.info(f"Running scraping job {job_id}")
        
        leads_found = []
        
        # Scrape from each source
        for source in sources:
            if source == 'google_search':
                results = scraper_service.scrape_google_search(keywords, locations, max_leads // len(sources))
                leads_found.extend(results)
            elif source == 'yellow_pages':
                results = scraper_service.scrape_yellow_pages(keywords, locations, max_leads // len(sources))
                leads_found.extend(results)
            elif source == 'business_directories':
                results = scraper_service.scrape_business_directories(keywords, locations, max_leads // len(sources))
                leads_found.extend(results)
        
        # Update job progress
        scraping_jobs[job_id]['total_leads'] = len(leads_found)
        
        # Process and save leads
        processed_count = 0
        for lead_data in leads_found:
            try:
                # Create lead
                lead = lead_manager.create_lead(lead_data)
                
                # Analyze with AI if requested
                if analyze_with_ai:
                    analysis = ai_analyzer.analyze_lead(lead)
                    lead_manager.update_lead(lead.id, {
                        'ai_analysis': analysis,
                        'score': analysis.get('score', 50)
                    })
                
                processed_count += 1
                scraping_jobs[job_id]['processed_leads'] = processed_count
                
            except Exception as e:
                scraping_jobs[job_id]['errors'].append(str(e))
                logger.error(f"Error processing lead: {str(e)}")
        
        # Mark job as completed
        scraping_jobs[job_id]['status'] = 'completed'
        scraping_jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Scraping job {job_id} completed. Processed {processed_count} leads.")
        
    except Exception as e:
        scraping_jobs[job_id]['status'] = 'failed'
        scraping_jobs[job_id]['errors'].append(str(e))
        logger.error(f"Scraping job {job_id} failed: {str(e)}")


@scraper_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a scraping job"""
    try:
        if job_id not in scraping_jobs:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': scraping_jobs[job_id]
        })
        
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraper_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all scraping jobs"""
    try:
        jobs = list(scraping_jobs.values())
        jobs.sort(key=lambda x: x['started_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'jobs': jobs,
                'total': len(jobs)
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraper_bp.route('/stop/<job_id>', methods=['POST'])
def stop_job(job_id):
    """Stop a running scraping job"""
    try:
        if job_id not in scraping_jobs:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        scraping_jobs[job_id]['status'] = 'stopped'
        scraping_jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Stopped scraping job: {job_id}")
        
        return jsonify({
            'success': True,
            'message': 'Job stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Error stopping job: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraper_bp.route('/preview', methods=['POST'])
def preview_scraping():
    """Preview scraping results without saving"""
    try:
        data = request.get_json() or {}
        
        keywords = data.get('keywords', ['fragrance retail'])
        locations = data.get('locations', ['Sydney, NSW'])
        max_leads = min(data.get('max_leads', 10), 20)  # Limit preview to 20
        
        # Quick scrape for preview
        results = scraper_service.scrape_google_search(keywords, locations, max_leads)
        
        # Analyze sample leads
        analyzed_results = []
        for result in results[:5]:  # Only analyze first 5 for preview
            analysis = ai_analyzer.quick_analyze(result)
            result['preview_analysis'] = analysis
            analyzed_results.append(result)
        
        return jsonify({
            'success': True,
            'data': {
                'preview_leads': analyzed_results,
                'total_found': len(results),
                'message': 'Preview generated successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@scraper_bp.route('/config', methods=['GET'])
def get_scraper_config():
    """Get current scraper configuration"""
    try:
        config = {
            'target_industries': current_app.config.get('TARGET_INDUSTRIES', []),
            'target_locations': current_app.config.get('TARGET_LOCATIONS', []),
            'max_leads_per_run': current_app.config.get('MAX_LEADS_PER_RUN', 100),
            'scraping_delay': current_app.config.get('SCRAPING_DELAY', 2),
            'available_sources': ['google_search', 'yellow_pages', 'business_directories']
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        logger.error(f"Error fetching scraper config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

