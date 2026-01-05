"""
Lead Manager Service
Handles lead storage, retrieval, and management
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime
from loguru import logger
import json
import os

from app.models.lead import Lead, LeadStatus, LeadPriority


class LeadManager:
    """Service for managing leads"""
    
    def __init__(self):
        """Initialize lead manager with in-memory storage"""
        self._leads: Dict[str, Lead] = {}
        self._data_file = 'data/leads.json'
        self._load_leads()
    
    def _load_leads(self):
        """Load leads from file storage"""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, 'r') as f:
                    data = json.load(f)
                    for lead_data in data:
                        lead = Lead.from_dict(lead_data)
                        self._leads[lead.id] = lead
                logger.info(f"Loaded {len(self._leads)} leads from storage")
        except Exception as e:
            logger.error(f"Error loading leads: {str(e)}")
            # Initialize with sample data for demo
            self._init_sample_data()
    
    def _save_leads(self):
        """Save leads to file storage"""
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            with open(self._data_file, 'w') as f:
                data = [lead.to_dict() for lead in self._leads.values()]
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved {len(self._leads)} leads to storage")
        except Exception as e:
            logger.error(f"Error saving leads: {str(e)}")
    
    def _init_sample_data(self):
        """Initialize with sample lead data"""
        sample_leads = [
            {
                'company_name': 'Luxury Retail Group',
                'contact_name': 'Sarah Johnson',
                'email': 'sarah.johnson@luxuryretail.com',
                'phone': '+61 2 9876 5432',
                'website': 'www.luxuryretail.com',
                'industry': 'Retail',
                'location': 'Sydney, NSW',
                'score': 92,
                'status': 'new',
                'priority': 'high',
                'source': 'ai-generated',
                'estimated_value': 75000
            },
            {
                'company_name': 'Premium Hospitality Solutions',
                'contact_name': 'Michael Chen',
                'email': 'm.chen@premiumhosp.com',
                'phone': '+61 3 8765 4321',
                'website': 'www.premiumhosp.com',
                'industry': 'Hospitality',
                'location': 'Melbourne, VIC',
                'score': 87,
                'status': 'contacted',
                'priority': 'high',
                'source': 'ai-generated',
                'estimated_value': 45000
            },
            {
                'company_name': 'Boutique Chain Australia',
                'contact_name': 'Emma Wilson',
                'email': 'emma@boutiquechain.au',
                'phone': '+61 7 7654 3210',
                'website': 'www.boutiquechain.au',
                'industry': 'Fashion',
                'location': 'Brisbane, QLD',
                'score': 78,
                'status': 'qualified',
                'priority': 'medium',
                'source': 'manual',
                'estimated_value': 32000
            },
            {
                'company_name': 'Wellness Spa Network',
                'contact_name': 'David Brown',
                'email': 'david@wellnessspa.com',
                'phone': '+61 8 6543 2109',
                'website': 'www.wellnessspa.com',
                'industry': 'Wellness',
                'location': 'Perth, WA',
                'score': 85,
                'status': 'new',
                'priority': 'medium',
                'source': 'ai-generated',
                'estimated_value': 28000
            },
            {
                'company_name': 'Elite Hotels Sydney',
                'contact_name': 'James Miller',
                'email': 'jmiller@elitehotels.com.au',
                'phone': '+61 2 9123 4567',
                'website': 'www.elitehotels.com.au',
                'industry': 'Hospitality',
                'location': 'Sydney, NSW',
                'score': 94,
                'status': 'new',
                'priority': 'high',
                'source': 'ai-generated',
                'estimated_value': 120000
            }
        ]
        
        for lead_data in sample_leads:
            lead = Lead.from_dict(lead_data)
            self._leads[lead.id] = lead
        
        self._save_leads()
        logger.info(f"Initialized {len(sample_leads)} sample leads")
    
    def get_leads(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        industry: Optional[str] = None,
        location: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Lead], int]:
        """Get leads with optional filtering"""
        
        leads = list(self._leads.values())
        
        # Apply filters
        if status:
            leads = [l for l in leads if l.status.value == status]
        
        if priority:
            leads = [l for l in leads if l.priority.value == priority]
        
        if industry:
            leads = [l for l in leads if l.industry and industry.lower() in l.industry.lower()]
        
        if location:
            leads = [l for l in leads if l.location and location.lower() in l.location.lower()]
        
        if search:
            search_lower = search.lower()
            leads = [l for l in leads if (
                search_lower in l.company_name.lower() or
                (l.contact_name and search_lower in l.contact_name.lower()) or
                (l.email and search_lower in l.email.lower()) or
                (l.industry and search_lower in l.industry.lower())
            )]
        
        # Sort by score (highest first) then by created_at (newest first)
        leads.sort(key=lambda x: (-x.score, -x.created_at.timestamp()))
        
        total = len(leads)
        
        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated_leads = leads[start:end]
        
        return paginated_leads, total
    
    def get_lead_by_id(self, lead_id: str) -> Optional[Lead]:
        """Get a single lead by ID"""
        return self._leads.get(lead_id)
    
    def create_lead(self, data: Dict) -> Lead:
        """Create a new lead"""
        lead = Lead.from_dict(data)
        self._leads[lead.id] = lead
        self._save_leads()
        logger.info(f"Created lead: {lead.company_name} ({lead.id})")
        return lead
    
    def update_lead(self, lead_id: str, data: Dict) -> Optional[Lead]:
        """Update an existing lead"""
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        
        lead.update(data)
        self._save_leads()
        logger.info(f"Updated lead: {lead_id}")
        return lead
    
    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead"""
        if lead_id in self._leads:
            del self._leads[lead_id]
            self._save_leads()
            logger.info(f"Deleted lead: {lead_id}")
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get lead statistics"""
        leads = list(self._leads.values())
        
        # Count by status
        status_counts = {}
        for status in LeadStatus:
            status_counts[status.value] = len([l for l in leads if l.status == status])
        
        # Count by priority
        priority_counts = {}
        for priority in LeadPriority:
            priority_counts[priority.value] = len([l for l in leads if l.priority == priority])
        
        # Calculate averages
        total_value = sum(l.estimated_value for l in leads)
        avg_score = sum(l.score for l in leads) / len(leads) if leads else 0
        
        # Top industries
        industry_counts = {}
        for lead in leads:
            if lead.industry:
                industry_counts[lead.industry] = industry_counts.get(lead.industry, 0) + 1
        
        top_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_leads': len(leads),
            'by_status': status_counts,
            'by_priority': priority_counts,
            'total_estimated_value': total_value,
            'average_score': round(avg_score, 1),
            'top_industries': dict(top_industries),
            'new_this_month': len([l for l in leads if l.created_at.month == datetime.utcnow().month]),
            'high_priority_count': priority_counts.get('high', 0)
        }
    
    def bulk_update_status(self, lead_ids: List[str], new_status: str) -> int:
        """Update status for multiple leads"""
        updated_count = 0
        for lead_id in lead_ids:
            if self.update_lead(lead_id, {'status': new_status}):
                updated_count += 1
        return updated_count
    
    def get_all_leads(self) -> List[Lead]:
        """Get all leads without pagination"""
        return list(self._leads.values())

