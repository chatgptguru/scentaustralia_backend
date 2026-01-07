"""
Debug script to test Google search scraping
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.scraper_service import ScraperService
from loguru import logger

# Configure logger to show all messages
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Test Google search
scraper = ScraperService()

print("\n" + "="*60)
print("Testing Google Search Scraping")
print("="*60 + "\n")

# Test with simple keywords
keywords = ['fragrance']
locations = ['Sydney, NSW']

print(f"Keywords: {keywords}")
print(f"Locations: {locations}\n")

results = scraper.scrape_google_search(keywords, locations, max_results=10)

print(f"\n{'='*60}")
print(f"Results: {len(results)} leads found")
print(f"{'='*60}\n")

for i, lead in enumerate(results, 1):
    print(f"{i}. {lead.get('company_name')}")
    print(f"   Website: {lead.get('website')}")
    print(f"   Email: {lead.get('email')}")
    print(f"   Phone: {lead.get('phone')}")
    print()
