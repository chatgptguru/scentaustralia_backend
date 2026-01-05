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
    
    # Scraping Configuration
    SCRAPING_DELAY = int(os.getenv('SCRAPING_DELAY', 2))
    MAX_LEADS_PER_RUN = int(os.getenv('MAX_LEADS_PER_RUN', 100))
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Request timeout
    REQUEST_TIMEOUT = 30
    
    # Data Export Configuration
    EXPORT_FOLDER = os.getenv('EXPORT_FOLDER', 'exports')
    MAX_EXPORT_ROWS = int(os.getenv('MAX_EXPORT_ROWS', 10000))
    
    # Lead Sources Configuration
    LEAD_SOURCES = {
        'google_search': {
            'enabled': True,
            'base_url': 'https://www.google.com/search',
            'max_pages': 5
        },
        'linkedin': {
            'enabled': False,  # Requires special handling
            'base_url': 'https://www.linkedin.com'
        },
        'yellow_pages': {
            'enabled': True,
            'base_url': 'https://www.yellowpages.com.au'
        },
        'business_directories': {
            'enabled': True,
            'urls': [
                'https://www.hotfrog.com.au',
                'https://www.truelocal.com.au'
            ]
        }
    }
    
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
        'Sydney, NSW',
        'Melbourne, VIC',
        'Brisbane, QLD',
        'Perth, WA',
        'Adelaide, SA',
        'Hobart, TAS',
        'Darwin, NT',
        'Canberra, ACT'
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

