"""
Application Configuration
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    # Azure OpenAI Configuration (alternative)
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '')
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', '')
    
    # Use Azure if Azure key is provided, otherwise use OpenAI
    USE_AZURE_OPENAI = bool(AZURE_OPENAI_API_KEY)
    
    # Apollo.io Configuration
    APOLLO_API_KEY = os.getenv('APOLLO_API_KEY', '')
    APOLLO_MAX_LEADS_PER_SEARCH = int(os.getenv('APOLLO_MAX_LEADS_PER_SEARCH', 100))
    
    # Request timeout
    REQUEST_TIMEOUT = 30
    
    # Data Export Configuration
    EXPORT_FOLDER = os.getenv('EXPORT_FOLDER', 'exports')
    MAX_EXPORT_ROWS = int(os.getenv('MAX_EXPORT_ROWS', 10000))
    
    # Industry Keywords for Scent Australia
    TARGET_INDUSTRIES = [
        'fragrance',
        'perfume',
        'scent marketing',
        'essential oils',
        'aromatherapy',
        'hotel amenities',
        'luxury retail',
        'boutique stores',
        'spa wellness',
        'hospitality',
        'commercial fragrance',
        'air freshener',
        'scent diffuser'
    ]
    
    # Australian Locations to Target
    TARGET_LOCATIONS = [
        'Sydney, Australia',
        'Melbourne, Australia',
        'Brisbane, Australia',
        'Perth, Australia',
        'Adelaide, Australia',
        'Hobart, Australia',
        'Darwin, Australia',
        'Canberra, Australia'
    ]
    
    # Default job titles for lead search
    TARGET_JOB_TITLES = [
        'Owner',
        'Founder',
        'CEO',
        'Managing Director',
        'General Manager',
        'Marketing Director',
        'Operations Manager',
        'Purchasing Manager',
        'Procurement Manager',
        'Facilities Manager'
    ]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
