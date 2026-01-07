"""
Web Scraping Module - Usage Examples and Tests
Demonstrates how to use the web scraping module for lead generation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.web_scraper import WebScraper, scrape_business_info
from app.services.scraping_job_manager import ScrapingJobManager, JobStatus
from app.services.data_extractor import LeadDataProcessor
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    lambda msg: print(msg, end=''),
    format="{time:HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)


def example_1_basic_scraping():
    """Example 1: Basic website scraping"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Website Scraping")
    print("="*60 + "\n")
    
    scraper = WebScraper(use_selenium=False)
    
    # Scrape a sample business website
    url = "https://www.examplecompany.com"
    
    result = scraper.scrape_business_listing(url)
    
    print(f"Company Name: {result['company_name']}")
    print(f"Emails: {result['emails']}")
    print(f"Phones: {result['phones']}")
    print(f"Address: {result['address']}")
    print(f"Social Links: {result['social_links']}")
    
    scraper.close_driver()


def example_2_search_and_scrape():
    """Example 2: Search and scrape based on keywords"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Search and Scrape")
    print("="*60 + "\n")
    
    scraper = WebScraper(use_selenium=False)
    
    keywords = ['fragrance', 'perfume', 'scent']
    locations = ['Sydney, NSW', 'Melbourne, VIC']
    
    leads = scraper.search_and_scrape(
        keywords=keywords,
        locations=locations,
        max_results=10,
        search_engine='google'
    )
    
    print(f"Found {len(leads)} leads:\n")
    
    for i, lead in enumerate(leads, 1):
        print(f"{i}. {lead.get('company_name', 'N/A')}")
        print(f"   Email: {lead.get('email', 'N/A')}")
        print(f"   Phone: {lead.get('phone', 'N/A')}")
        print(f"   Industry: {lead.get('industry', 'N/A')}")
        print(f"   Location: {lead.get('location', 'N/A')}")
        print()
    
    scraper.close_driver()


def example_3_email_extraction():
    """Example 3: Extract multiple emails from text"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Email Extraction")
    print("="*60 + "\n")
    
    scraper = WebScraper()
    
    sample_text = """
    Contact us:
    Email: info@fragrance.com.au
    Support: support@fragrance.com.au
    Sales: sales@fragrance.com.au
    General inquiries: hello@fragrance.com.au
    """
    
    emails = scraper.extract_emails(sample_text, limit=5)
    
    print(f"Extracted {len(emails)} emails:")
    for email in emails:
        print(f"  - {email}")
    
    scraper.close_driver()


def example_4_phone_extraction():
    """Example 4: Extract phone numbers"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Phone Number Extraction")
    print("="*60 + "\n")
    
    scraper = WebScraper()
    
    sample_text = """
    Contact Information:
    Main: +61 2 9123 4567
    Local: 0412 345 678
    Toll Free: 1300 123 456
    Office: (02) 9123 4567
    """
    
    phones = scraper.extract_phones(sample_text, country='AU', limit=5)
    
    print(f"Extracted {len(phones)} phone numbers:")
    for phone in phones:
        print(f"  - {phone}")
    
    scraper.close_driver()


def example_5_data_validation():
    """Example 5: Validate extracted data"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Data Validation")
    print("="*60 + "\n")
    
    processor = LeadDataProcessor()
    
    # Sample leads with various validity levels
    sample_leads = [
        {
            'company_name': 'Scent Australia Pty Ltd',
            'email': 'info@scentaustralia.com.au',
            'phone': '+61 2 9123 4567',
            'address': '123 Pitt Street, Sydney NSW 2000',
            'website': 'https://www.scentaustralia.com.au'
        },
        {
            'company_name': 'Invalid Company',
            'email': 'invalid-email',
            'phone': '123',
            'address': 'Too short'
        },
        {
            'company_name': 'Another Business',
            'email': 'contact@anotherbiz.com.au',
            'phone': '0412 345 678'
        }
    ]
    
    for i, lead in enumerate(sample_leads, 1):
        print(f"Lead {i}: {lead['company_name']}")
        
        processed_lead, validation = processor.process_lead(lead)
        
        print(f"  Valid: {validation.is_valid}")
        print(f"  Confidence: {validation.confidence:.1f}%")
        
        if validation.errors:
            print(f"  Errors: {', '.join(validation.errors)}")
        
        if validation.warnings:
            print(f"  Warnings: {', '.join(validation.warnings)}")
        
        print()


def example_6_batch_processing():
    """Example 6: Process multiple leads in batch"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Batch Lead Processing")
    print("="*60 + "\n")
    
    processor = LeadDataProcessor()
    
    # Sample batch of leads
    leads = [
        {
            'company_name': 'Company A',
            'email': 'info@companya.com.au',
            'phone': '+61 2 1234 5678',
        },
        {
            'company_name': 'Company B',
            'email': 'contact@companyb.com',
        },
        {
            'company_name': 'Company C',
            'phone': '0412 345 678',
        }
    ]
    
    processed_leads, stats = processor.process_leads_batch(leads)
    
    print("Batch Processing Statistics:")
    print(f"  Total Leads: {stats['total_leads']}")
    print(f"  Valid Leads: {stats['valid_leads']}")
    print(f"  Invalid Leads: {stats['invalid_leads']}")
    print(f"  Average Confidence: {stats['average_confidence']:.1f}%")


def example_7_job_management():
    """Example 7: Manage scraping jobs"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Scraping Job Management")
    print("="*60 + "\n")
    
    job_manager = ScrapingJobManager()
    
    # Create a new job
    job = job_manager.create_job(
        keywords=['fragrance', 'perfume'],
        locations=['Sydney, NSW', 'Melbourne, VIC'],
        sources=['google_search', 'yellow_pages'],
        max_leads=50,
        use_ai_analysis=True,
        notes='Initial scraping campaign'
    )
    
    print(f"Created Job: {job.job_id}")
    print(f"Status: {job.status.value}")
    print(f"Max Leads: {job.max_leads}")
    print(f"Keywords: {', '.join(job.keywords)}")
    print(f"Locations: {', '.join(job.locations)}")
    
    # Update job status
    job_manager.update_job_status(job.job_id, JobStatus.RUNNING)
    print(f"\nUpdated Status: RUNNING")
    
    # Update progress
    job_manager.update_job_progress(
        job.job_id,
        leads_found=25,
        leads_processed=20,
        leads_validated=18
    )
    
    job = job_manager.get_job(job.job_id)
    print(f"Progress: {job.get_progress_percentage():.1f}%")
    print(f"Leads Found: {job.total_leads_found}")
    print(f"Leads Processed: {job.leads_processed}")
    
    # Complete job
    job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
    
    # Get statistics
    stats = job_manager.get_job_statistics()
    print(f"\nJob Statistics:")
    print(f"  Total Jobs: {stats['total_jobs']}")
    print(f"  Total Leads Found: {stats['total_leads_found']}")
    print(f"  By Status: {stats['by_status']}")


def example_8_social_link_extraction():
    """Example 8: Extract social media links"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Social Media Link Extraction")
    print("="*60 + "\n")
    
    from bs4 import BeautifulSoup
    
    scraper = WebScraper()
    
    # Sample HTML with social links
    html = """
    <html>
        <body>
            <a href="https://www.facebook.com/fragrance">Follow us on Facebook</a>
            <a href="https://www.linkedin.com/company/fragrance">LinkedIn</a>
            <a href="https://twitter.com/fragrance">Twitter</a>
            <a href="https://www.instagram.com/fragrance">Instagram</a>
            <a href="https://www.youtube.com/fragrance">YouTube</a>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    social_links = scraper.extract_social_links(soup, 'https://example.com')
    
    print("Extracted Social Media Links:")
    for platform, urls in social_links.items():
        print(f"  {platform.upper()}: {urls}")
    
    scraper.close_driver()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  WEB SCRAPING MODULE - EXAMPLES AND TESTS            ║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Run examples
        example_3_email_extraction()
        example_4_phone_extraction()
        example_5_data_validation()
        example_6_batch_processing()
        example_7_job_management()
        example_8_social_link_extraction()
        
        # The following examples require actual web access and are commented out
        # example_1_basic_scraping()
        # example_2_search_and_scrape()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error running examples: {str(e)}")
        raise


if __name__ == '__main__':
    main()
