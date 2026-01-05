"""
Lead Data Model
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
import uuid


class LeadStatus(str, Enum):
    """Lead status enumeration"""
    NEW = 'new'
    CONTACTED = 'contacted'
    QUALIFIED = 'qualified'
    CONVERTED = 'converted'
    LOST = 'lost'


class LeadPriority(str, Enum):
    """Lead priority enumeration"""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class LeadSource(str, Enum):
    """Lead source enumeration"""
    AI_GENERATED = 'ai-generated'
    MANUAL = 'manual'
    IMPORTED = 'imported'
    GOOGLE_SEARCH = 'google-search'
    YELLOW_PAGES = 'yellow-pages'
    LINKEDIN = 'linkedin'
    BUSINESS_DIRECTORY = 'business-directory'


@dataclass
class Lead:
    """Lead data class"""
    
    # Basic Information
    company_name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Contact Information
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Business Information
    industry: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    
    # Lead Details
    status: LeadStatus = LeadStatus.NEW
    priority: LeadPriority = LeadPriority.MEDIUM
    source: LeadSource = LeadSource.AI_GENERATED
    score: int = 50  # 0-100 score
    
    # AI Analysis
    ai_analysis: Optional[Dict] = None
    ai_score_breakdown: Optional[Dict] = None
    
    # Notes and Tags
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_contacted: Optional[datetime] = None
    source_url: Optional[str] = None
    
    # Estimated Value
    estimated_value: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert lead to dictionary"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'industry': self.industry,
            'location': self.location,
            'address': self.address,
            'company_size': self.company_size,
            'annual_revenue': self.annual_revenue,
            'status': self.status.value if isinstance(self.status, LeadStatus) else self.status,
            'priority': self.priority.value if isinstance(self.priority, LeadPriority) else self.priority,
            'source': self.source.value if isinstance(self.source, LeadSource) else self.source,
            'score': self.score,
            'ai_analysis': self.ai_analysis,
            'ai_score_breakdown': self.ai_score_breakdown,
            'notes': self.notes,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_contacted': self.last_contacted.isoformat() if self.last_contacted else None,
            'source_url': self.source_url,
            'estimated_value': self.estimated_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Lead':
        """Create lead from dictionary"""
        # Handle status conversion
        status = data.get('status', 'new')
        if isinstance(status, str):
            status = LeadStatus(status)
        
        # Handle priority conversion
        priority = data.get('priority', 'medium')
        if isinstance(priority, str):
            priority = LeadPriority(priority)
        
        # Handle source conversion
        source = data.get('source', 'ai-generated')
        if isinstance(source, str):
            try:
                source = LeadSource(source)
            except ValueError:
                source = LeadSource.AI_GENERATED
        
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()
        
        last_contacted = data.get('last_contacted')
        if isinstance(last_contacted, str):
            last_contacted = datetime.fromisoformat(last_contacted)
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            company_name=data.get('company_name', ''),
            contact_name=data.get('contact_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            website=data.get('website'),
            industry=data.get('industry'),
            location=data.get('location'),
            address=data.get('address'),
            company_size=data.get('company_size'),
            annual_revenue=data.get('annual_revenue'),
            status=status,
            priority=priority,
            source=source,
            score=data.get('score', 50),
            ai_analysis=data.get('ai_analysis'),
            ai_score_breakdown=data.get('ai_score_breakdown'),
            notes=data.get('notes'),
            tags=data.get('tags', []),
            created_at=created_at,
            updated_at=updated_at,
            last_contacted=last_contacted,
            source_url=data.get('source_url'),
            estimated_value=data.get('estimated_value', 0.0)
        )
    
    def update(self, data: Dict) -> None:
        """Update lead with new data"""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                if key == 'status' and isinstance(value, str):
                    value = LeadStatus(value)
                elif key == 'priority' and isinstance(value, str):
                    value = LeadPriority(value)
                elif key == 'source' and isinstance(value, str):
                    try:
                        value = LeadSource(value)
                    except ValueError:
                        continue
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()

