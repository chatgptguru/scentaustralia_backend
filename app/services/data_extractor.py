"""
Data Extraction and Validation Module
Uses AI to extract and validate lead data with intelligent parsing
"""

from typing import List, Dict, Optional, Tuple
from loguru import logger
import re
from datetime import datetime
from dataclasses import dataclass
import json

from app.config import Config


@dataclass
class ValidationResult:
    """Data validation result"""
    is_valid: bool
    confidence: float  # 0-100
    errors: List[str]
    warnings: List[str]
    cleaned_data: Dict
    ai_suggestions: Optional[str] = None


class DataExtractor:
    """Extract structured data from raw scraped content"""
    
    def __init__(self):
        """Initialize data extractor"""
        self.config = Config()
    
    def extract_contact_info(self, text: str) -> Dict:
        """
        Extract structured contact information from text
        
        Args:
            text: Raw text content
        
        Returns:
            Dictionary with contact information
        """
        result = {
            'emails': [],
            'phones': [],
            'addresses': [],
            'websites': [],
            'social_profiles': {}
        }
        
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        result['emails'] = list(set(re.findall(email_pattern, text)))
        
        # Extract Australian phone numbers
        phone_patterns = [
            r'\+61\s*[2-9]\s*\d{4}\s*\d{4}',
            r'0[2-9]\s*\d{4}\s*\d{4}',
            r'\(0[2-9]\)\s*\d{4}\s*\d{4}',
            r'1[38]00\s*\d{3}\s*\d{3}',
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            result['phones'].extend(matches)
        
        result['phones'] = list(set(result['phones']))
        
        # Extract URLs
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        result['websites'] = list(set(re.findall(url_pattern, text)))
        
        return result
    
    def extract_business_info(self, text: str) -> Dict:
        """
        Extract business information from text
        
        Args:
            text: Raw text content
        
        Returns:
            Dictionary with business information
        """
        result = {
            'industry_keywords': [],
            'business_size_indicators': [],
            'revenue_indicators': [],
            'locations': [],
            'company_types': []
        }
        
        text_lower = text.lower()
        
        # Industry keywords
        industry_terms = {
            'fragrance': ['fragrance', 'perfume', 'scent', 'aroma'],
            'retail': ['retail', 'store', 'shop', 'boutique'],
            'spa_wellness': ['spa', 'wellness', 'massage', 'therapy'],
            'hospitality': ['hotel', 'resort', 'restaurant', 'cafe'],
            'real_estate': ['property', 'real estate', 'estate agent', 'realty'],
            'it_services': ['software', 'it services', 'web development', 'consulting'],
        }
        
        for industry, keywords in industry_terms.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result['industry_keywords'].append(industry)
                    break
        
        # Company size indicators
        size_indicators = {
            'large': ['enterprise', 'corporation', 'multinational', '1000+'],
            'medium': ['mid-size', '50-1000', 'company', 'organization'],
            'small': ['startup', 'small business', 'solopreneur', '1-50']
        }
        
        for size, indicators in size_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    result['business_size_indicators'].append(size)
        
        # Revenue indicators
        revenue_pattern = r'\$[\d,]+(?:\s*(?:million|billion|thousand|k|m|b))?'
        result['revenue_indicators'] = re.findall(revenue_pattern, text, re.IGNORECASE)
        
        # Company types
        company_types = {
            'pty_ltd': ['pty', 'pty ltd', 'pty. ltd'],
            'limited': ['limited', 'ltd', 'ltd.'],
            'inc': ['inc', 'inc.', 'incorporated'],
            'sole_trader': ['sole trader', 'abn'],
            'partnership': ['partnership', 'partners']
        }
        
        for comp_type, indicators in company_types.items():
            for indicator in indicators:
                if indicator in text_lower:
                    result['company_types'].append(comp_type)
        
        return result
    
    def extract_location(self, text: str) -> Dict:
        """
        Extract location information from text
        
        Args:
            text: Raw text content
        
        Returns:
            Dictionary with location information
        """
        result = {
            'addresses': [],
            'postcodes': [],
            'suburbs': [],
            'states': [],
            'countries': []
        }
        
        # Australian postcodes
        postcode_pattern = r'\b[0-9]{4}\s+[A-Z]{2}\b'
        result['postcodes'] = list(set(re.findall(postcode_pattern, text)))
        
        # Australian states
        states = {
            'NSW': ['new south wales', 'nsw'],
            'VIC': ['victoria', 'vic'],
            'QLD': ['queensland', 'qld'],
            'WA': ['western australia', 'wa'],
            'SA': ['south australia', 'sa'],
            'TAS': ['tasmania', 'tas'],
            'NT': ['northern territory', 'nt'],
            'ACT': ['australian capital territory', 'act']
        }
        
        text_lower = text.lower()
        for state, keywords in states.items():
            for keyword in keywords:
                if keyword in text_lower:
                    result['states'].append(state)
                    break
        
        result['states'] = list(set(result['states']))
        
        return result


class DataValidator:
    """Validate extracted lead data"""
    
    def __init__(self):
        """Initialize validator"""
        self.config = Config()
    
    def validate_email(self, email: str) -> Tuple[bool, float]:
        """
        Validate email address
        
        Returns:
            Tuple of (is_valid, confidence)
        """
        if not email or not isinstance(email, str):
            return False, 0.0
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False, 0.0
        
        # Check for suspicious patterns
        suspicious_patterns = ['test@', 'admin@', 'noreply@', 'donotreply@']
        for pattern in suspicious_patterns:
            if email.lower().startswith(pattern):
                return True, 0.5
        
        # Check domain
        domain = email.split('@')[1].lower()
        
        # Personal email domains (lower confidence)
        personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'}
        if domain in personal_domains:
            return True, 0.6
        
        # Business email (high confidence)
        if domain.count('.') >= 1:
            return True, 0.95
        
        return True, 0.8
    
    def validate_phone(self, phone: str, country: str = 'AU') -> Tuple[bool, float]:
        """
        Validate phone number
        
        Returns:
            Tuple of (is_valid, confidence)
        """
        if not phone or not isinstance(phone, str):
            return False, 0.0
        
        # Remove common formatting
        cleaned = re.sub(r'[\s\-\(\)\.+]', '', phone)
        
        # Australian phone validation
        if country == 'AU':
            # Format: +61 X XXXX XXXX or 0X XXXX XXXX or 1300/1800
            if len(cleaned) < 9 or len(cleaned) > 12:
                return False, 0.0
            
            # Check for valid patterns
            if cleaned.startswith('61'):
                # International format
                return True, 0.9
            elif cleaned.startswith('0'):
                # National format
                return True, 0.95
            elif cleaned.startswith('1'):
                # 1300/1800 numbers
                return True, 0.85
        
        return False, 0.0
    
    def validate_website(self, url: str) -> Tuple[bool, float]:
        """
        Validate website URL
        
        Returns:
            Tuple of (is_valid, confidence)
        """
        if not url or not isinstance(url, str):
            return False, 0.0
        
        url_pattern = r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'
        
        if re.match(url_pattern, url):
            return True, 0.9
        
        return False, 0.0
    
    def validate_company_name(self, name: str) -> Tuple[bool, float]:
        """
        Validate company name
        
        Returns:
            Tuple of (is_valid, confidence)
        """
        if not name or not isinstance(name, str):
            return False, 0.0
        
        # Check length
        if len(name) < 2 or len(name) > 200:
            return False, 0.0
        
        # Check for suspicious patterns
        if any(word in name.lower() for word in ['linkedin', 'facebook', 'twitter', 'yelp', 'wikipedia']):
            return False, 0.1
        
        # Check for spam indicators
        if name.count(' ') > 10 or name.count('!') > 2:
            return False, 0.2
        
        # Basic validation passed
        return True, 0.8
    
    def validate_address(self, address: str, country: str = 'AU') -> Tuple[bool, float]:
        """
        Validate address
        
        Returns:
            Tuple of (is_valid, confidence)
        """
        if not address or not isinstance(address, str):
            return False, 0.0
        
        # Check length
        if len(address) < 5 or len(address) > 500:
            return False, 0.0
        
        # Check for postcode in Australian addresses
        if country == 'AU':
            postcode_pattern = r'\b[0-9]{4}\s+[A-Z]{2}\b'
            if re.search(postcode_pattern, address):
                return True, 0.95
        
        # Contains numbers and at least 3 words
        if any(c.isdigit() for c in address) and len(address.split()) >= 3:
            return True, 0.7
        
        return True, 0.5
    
    def validate_lead(self, lead_data: Dict) -> ValidationResult:
        """
        Validate complete lead data
        
        Args:
            lead_data: Lead dictionary
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        confidence = 100.0
        cleaned_data = lead_data.copy()
        
        # Validate company name
        if not lead_data.get('company_name'):
            errors.append("Company name is required")
            confidence *= 0.5
        else:
            is_valid, conf = self.validate_company_name(lead_data['company_name'])
            if not is_valid:
                errors.append(f"Invalid company name: {lead_data['company_name']}")
                confidence *= conf
            else:
                confidence *= conf
        
        # Validate email
        if lead_data.get('email'):
            is_valid, conf = self.validate_email(lead_data['email'])
            if not is_valid:
                errors.append(f"Invalid email: {lead_data['email']}")
                cleaned_data['email'] = None
                confidence *= 0.7
            else:
                confidence *= conf
        else:
            warnings.append("No email found")
            confidence *= 0.8
        
        # Validate phone
        if lead_data.get('phone'):
            is_valid, conf = self.validate_phone(lead_data['phone'])
            if not is_valid:
                warnings.append(f"Invalid phone: {lead_data['phone']}")
                cleaned_data['phone'] = None
                confidence *= 0.8
            else:
                confidence *= conf
        else:
            warnings.append("No phone found")
            confidence *= 0.9
        
        # Validate website
        if lead_data.get('website'):
            is_valid, conf = self.validate_website(lead_data['website'])
            if not is_valid:
                warnings.append(f"Invalid website: {lead_data['website']}")
                cleaned_data['website'] = None
                confidence *= 0.85
            else:
                confidence *= conf
        
        # Validate address
        if lead_data.get('address'):
            is_valid, conf = self.validate_address(lead_data['address'])
            if not is_valid:
                warnings.append(f"Invalid address: {lead_data['address']}")
                cleaned_data['address'] = None
                confidence *= 0.85
            else:
                confidence *= conf
        
        # Ensure confidence is between 0-100
        confidence = max(0, min(100, confidence))
        
        is_valid = len(errors) == 0 and confidence > 30.0
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data
        )


class LeadDataProcessor:
    """Process and enrich lead data"""
    
    def __init__(self):
        """Initialize processor"""
        self.extractor = DataExtractor()
        self.validator = DataValidator()
    
    def process_lead(self, lead_data: Dict) -> Tuple[Dict, ValidationResult]:
        """
        Process and validate lead data
        
        Args:
            lead_data: Raw lead data
        
        Returns:
            Tuple of (processed_data, validation_result)
        """
        # Validate lead
        validation_result = self.validator.validate_lead(lead_data)
        
        # Use cleaned data from validation
        processed_data = validation_result.cleaned_data.copy()
        
        # Add validation metadata
        processed_data['validation'] = {
            'is_valid': validation_result.is_valid,
            'confidence': validation_result.confidence,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'validated_at': datetime.utcnow().isoformat()
        }
        
        # Add processing metadata
        if 'processed_at' not in processed_data:
            processed_data['processed_at'] = datetime.utcnow().isoformat()
        
        return processed_data, validation_result
    
    def process_leads_batch(self, leads: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Process multiple leads
        
        Args:
            leads: List of lead dictionaries
        
        Returns:
            Tuple of (processed_leads, statistics)
        """
        processed_leads = []
        statistics = {
            'total_leads': len(leads),
            'valid_leads': 0,
            'invalid_leads': 0,
            'average_confidence': 0.0,
            'processed_at': datetime.utcnow().isoformat()
        }
        
        total_confidence = 0.0
        
        for lead in leads:
            processed_lead, validation_result = self.process_lead(lead)
            processed_leads.append(processed_lead)
            
            if validation_result.is_valid:
                statistics['valid_leads'] += 1
            else:
                statistics['invalid_leads'] += 1
            
            total_confidence += validation_result.confidence
        
        if len(leads) > 0:
            statistics['average_confidence'] = total_confidence / len(leads)
        
        return processed_leads, statistics
