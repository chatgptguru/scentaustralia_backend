"""
Apollo.io Routes
API endpoints for Apollo.io lead generation
"""

from flask import Blueprint, jsonify, request, current_app
from loguru import logger
from datetime import datetime
import threading
import asyncio

from app.services.apollo_service import ApolloService
from app.services.shared_services import lead_manager, ai_analyzer

apollo_bp = Blueprint('apollo', __name__)

# Initialize services
apollo_service = ApolloService()

# Store for tracking search jobs
search_jobs = {}


@apollo_bp.route('/search/people', methods=['POST'])
def search_people():
    """Search for people/contacts using Apollo.io"""
    try:
        data = request.get_json() or {}
        
        # Get search parameters
        person_titles = data.get('person_titles', [])
        person_locations = data.get('person_locations', [])
        organization_locations = data.get('organization_locations', [])
        organization_industries = data.get('organization_industries', [])
        q_keywords = data.get('keywords', '')
        per_page = min(data.get('per_page', 25), 100)
        page = data.get('page', 1)
        
        # Run async search
        result = asyncio.run(apollo_service.search_people(
            person_titles=person_titles if person_titles else None,
            person_locations=person_locations if person_locations else None,
            organization_locations=organization_locations if organization_locations else None,
            organization_industries=organization_industries if organization_industries else None,
            q_keywords=q_keywords if q_keywords else None,
            per_page=per_page,
            page=page
        ))
        
        if not result.get('success'):
            # Return 403 if it's an access denied error
            status_code = 403 if result.get('error_code') == 'ACCESS_DENIED' or 'does not have access' in result.get('error', '') else 400
            return jsonify({
                'success': False,
                'error': result.get('error', 'Search failed'),
                'error_code': result.get('error_code')
            }), status_code
        
        # Transform people to lead format
        leads = [
            apollo_service.transform_person_to_lead(person)
            for person in result.get('people', [])
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'leads': leads,
                'total': result.get('total', 0),
                'pagination': result.get('pagination', {}),
                'message': f'Found {len(leads)} contacts'
            }
        })
        
    except Exception as e:
        logger.error(f"Error searching people: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@apollo_bp.route('/search/organizations', methods=['POST'])
def search_organizations():
    """Search for organizations/companies using Apollo.io"""
    try:
        data = request.get_json() or {}
        
        organization_locations = data.get('organization_locations', [])
        organization_industries = data.get('organization_industries', [])
        q_keyword = data.get('keywords', '')
        per_page = min(data.get('per_page', 25), 100)
        page = data.get('page', 1)
        
        result = asyncio.run(apollo_service.search_organizations(
            organization_locations=organization_locations if organization_locations else None,
            organization_industries=organization_industries if organization_industries else None,
            q_organization_keyword=q_keyword if q_keyword else None,
            per_page=per_page,
            page=page
        ))
        
        if not result.get('success'):
            # Return 403 if it's an access denied error
            status_code = 403 if result.get('error_code') == 'ACCESS_DENIED' or 'does not have access' in result.get('error', '') else 400
            return jsonify({
                'success': False,
                'error': result.get('error', 'Search failed'),
                'error_code': result.get('error_code')
            }), status_code
        
        # Transform organizations to lead format
        leads = [
            apollo_service.transform_organization_to_lead(org)
            for org in result.get('organizations', [])
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'leads': leads,
                'total': result.get('total', 0),
                'pagination': result.get('pagination', {}),
                'message': f'Found {len(leads)} organizations'
            }
        })
        
    except Exception as e:
        logger.error(f"Error searching organizations: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@apollo_bp.route('/generate', methods=['POST'])
def generate_leads():
    """Generate and save leads from Apollo.io with AI analysis"""
    try:
        data = request.get_json() or {}
        
        # Get parameters
        search_type = data.get('search_type', 'people')  # 'people' or 'organizations'
        person_titles = data.get('person_titles', [])
        person_locations = data.get('person_locations', 
                                   current_app.config.get('TARGET_LOCATIONS', []))
        organization_locations = data.get('organization_locations', [])
        organization_industries = data.get('organization_industries', [])
        keywords = data.get('keywords', '')
        max_leads = min(data.get('max_leads', 50), 100)
        analyze_with_ai = data.get('analyze_with_ai', True)
        save_leads = data.get('save_leads', True)
        
        # Generate job ID
        job_id = f"apollo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize job status
        search_jobs[job_id] = {
            'id': job_id,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'total_leads': 0,
            'processed_leads': 0,
            'saved_leads': 0,
            'errors': [],
            'parameters': {
                'search_type': search_type,
                'person_titles': person_titles,
                'person_locations': person_locations,
                'organization_locations': organization_locations,
                'organization_industries': organization_industries,
                'keywords': keywords,
                'max_leads': max_leads,
                'analyze_with_ai': analyze_with_ai,
                'save_leads': save_leads
            }
        }
        
        # Start generation in background thread
        thread = threading.Thread(
            target=run_generation_job,
            args=(job_id, search_type, person_titles, person_locations,
                  organization_locations, organization_industries, keywords,
                  max_leads, analyze_with_ai, save_leads)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started Apollo lead generation job: {job_id}")
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'running',
                'message': 'Lead generation started successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting lead generation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_generation_job(job_id, search_type, person_titles, person_locations,
                       organization_locations, organization_industries, keywords,
                       max_leads, analyze_with_ai, save_leads):
    """Execute lead generation job in background"""
    try:
        logger.info(f"Running Apollo generation job {job_id}")
        
        leads_data = []
        
        # Perform search based on type
        if search_type == 'people':
            # First, search for people matching the filters
            result = asyncio.run(
                apollo_service.search_people(
                    person_titles=person_titles if person_titles else None,
                    person_locations=person_locations if person_locations else None,
                    organization_locations=organization_locations if organization_locations else None,
                    organization_industries=organization_industries if organization_industries else None,
                    q_keywords=keywords if keywords else None,
                    per_page=min(max_leads, 100),
                    page=1,
                )
            )

            if result.get('success'):
                people = result.get('people', [])[:max_leads]

                # Enrich each person to reveal emails & phones (uses credits per Apollo docs).
                enriched_people = []
                for idx, person in enumerate(people):
                    try:
                        # Extract available identifiers from search result
                        person_id = person.get("id")
                        email = person.get("email")
                        linkedin_url = person.get("linkedin_url")
                        first_name = person.get("first_name")
                        last_name = person.get("last_name")
                        org = person.get("organization", {}) or {}
                        organization_name = org.get("name") or person.get("organization_name")
                        domain = org.get("primary_domain") or org.get("website_url")
                        
                        logger.debug(f"Enriching person {idx+1}/{len(people)}: {first_name} {last_name} at {organization_name}")
                        
                        enriched_result = asyncio.run(
                            apollo_service.enrich_person(
                                email=email,
                                linkedin_url=linkedin_url,
                                person_id=person_id,
                                first_name=first_name,
                                last_name=last_name,
                                organization_name=organization_name,
                                domain=domain,
                                reveal_personal_emails=True,
                                reveal_phone_number=False,  # Only need emails, phone requires webhook_url
                            )
                        )
                        
                        if enriched_result.get("success") and enriched_result.get("person"):
                            enriched_person = enriched_result["person"]
                            enriched_email = enriched_person.get("email")
                            logger.info(f"Enrichment successful for {first_name} {last_name}: email={bool(enriched_email)}")
                            enriched_people.append(enriched_person)
                        else:
                            error_msg = enriched_result.get("error", "Unknown error")
                            logger.warning(f"Enrichment failed for {first_name} {last_name}: {error_msg}. Using original data.")
                            # Fallback to original person data if enrichment fails
                            enriched_people.append(person)
                    except Exception as enrich_err:
                        logger.error(f"Error enriching person {idx+1} from Apollo: {enrich_err}")
                        enriched_people.append(person)

                for person in enriched_people:
                    leads_data.append(apollo_service.transform_person_to_lead(person))
        else:
            result = asyncio.run(apollo_service.search_organizations(
                organization_locations=organization_locations if organization_locations else None,
                organization_industries=organization_industries if organization_industries else None,
                q_organization_keyword=keywords if keywords else None,
                per_page=min(max_leads, 100),
                page=1
            ))
            
            if result.get('success'):
                for org in result.get('organizations', [])[:max_leads]:
                    leads_data.append(apollo_service.transform_organization_to_lead(org))
        
        search_jobs[job_id]['total_leads'] = len(leads_data)
        logger.info(f"Found {len(leads_data)} leads from Apollo")
        
        # Process and save leads
        processed_count = 0
        saved_count = 0
        
        for lead_data in leads_data:
            try:
                # Analyze with AI if requested
                if analyze_with_ai:
                    analysis = ai_analyzer.analyze_lead_data(lead_data)
                    lead_data['ai_analysis'] = analysis
                    lead_data['score'] = analysis.get('score', 50)
                    lead_data['priority'] = analysis.get('priority', 'medium')
                
                # Save lead if requested
                if save_leads:
                    # Remove raw_data before saving (too large)
                    save_data = {k: v for k, v in lead_data.items() if k != 'raw_data'}
                    lead = lead_manager.create_lead(save_data)
                    saved_count += 1
                
                processed_count += 1
                search_jobs[job_id]['processed_leads'] = processed_count
                search_jobs[job_id]['saved_leads'] = saved_count
                
            except Exception as e:
                search_jobs[job_id]['errors'].append(str(e))
                logger.error(f"Error processing lead: {str(e)}")
        
        # Mark job as completed
        search_jobs[job_id]['status'] = 'completed'
        search_jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Apollo job {job_id} completed. Processed {processed_count}, Saved {saved_count}")
        
    except Exception as e:
        search_jobs[job_id]['status'] = 'failed'
        search_jobs[job_id]['errors'].append(str(e))
        logger.error(f"Apollo job {job_id} failed: {str(e)}")


@apollo_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of an Apollo lead generation job"""
    try:
        if job_id not in search_jobs:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': search_jobs[job_id]
        })
        
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@apollo_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all Apollo lead generation jobs"""
    try:
        jobs = list(search_jobs.values())
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


@apollo_bp.route('/enrich', methods=['POST'])
def enrich_contact():
    """Enrich a contact with additional data from Apollo"""
    try:
        data = request.get_json() or {}
        
        email = data.get('email')
        linkedin_url = data.get('linkedin_url')
        
        if not email and not linkedin_url:
            return jsonify({
                'success': False,
                'error': 'Email or LinkedIn URL required'
            }), 400
        
        result = asyncio.run(
            apollo_service.enrich_person(
                email=email,
                linkedin_url=linkedin_url,
                reveal_personal_emails=True,
                reveal_phone_number=False,  # Only need emails, phone requires webhook_url
            )
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Enrichment failed')
            }), 400
        
        # Transform to lead format
        lead_data = apollo_service.transform_person_to_lead(result.get('person', {}))
        
        return jsonify({
            'success': True,
            'data': {
                'lead': lead_data,
                'message': 'Contact enriched successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error enriching contact: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@apollo_bp.route('/config', methods=['GET'])
def get_apollo_config():
    """Get Apollo.io configuration and available options"""
    try:
        is_configured = apollo_service._is_configured()
        
        config = {
            'is_configured': is_configured,
            'target_locations': current_app.config.get('TARGET_LOCATIONS', []),
            'target_industries': current_app.config.get('TARGET_INDUSTRIES', []),
            'max_leads_per_search': 100,
            'available_filters': {
                'person_titles': ['CEO', 'Director', 'Manager', 'Owner', 'Founder', 'VP', 'Head of'],
                'employee_ranges': ['1,10', '11,50', '51,200', '201,500', '501,1000', '1001,5000'],
                'seniority_levels': ['owner', 'founder', 'c_suite', 'partner', 'vp', 'head', 'director', 'manager', 'senior', 'entry']
            },
            'search_types': ['people', 'organizations']
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        logger.error(f"Error fetching Apollo config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
