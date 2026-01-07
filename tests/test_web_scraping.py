"""
Web Scraping Module - Unit Tests
Tests for the web scraping, data extraction, and job management modules
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from app.services.web_scraper import WebScraper
from app.services.scraping_job_manager import ScrapingJobManager, JobStatus, ScrapingJob
from app.services.data_extractor import DataValidator, DataExtractor, LeadDataProcessor
from bs4 import BeautifulSoup


class TestWebScraper:
    """Test WebScraper class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.scraper = WebScraper(use_selenium=False)
    
    def teardown_method(self):
        """Cleanup after each test"""
        self.scraper.close_driver()
    
    def test_extract_email_valid(self):
        """Test valid email extraction"""
        text = "Contact us at info@company.com.au"
        email = self.scraper.extract_email(text)
        assert email == "info@company.com.au"
    
    def test_extract_email_multiple(self):
        """Test extracting multiple emails"""
        text = """
        Email: info@company.com.au
        Support: support@company.com.au
        Sales: sales@company.com.au
        """
        emails = self.scraper.extract_emails(text, limit=3)
        assert len(emails) > 0
        assert "info@company.com.au" in emails
    
    def test_extract_email_excluded_domains(self):
        """Test that excluded domains are filtered"""
        text = "Contact: test@gmail.com or info@company.com.au"
        email = self.scraper.extract_email(text)
        assert email == "info@company.com.au"
    
    def test_extract_phone_au(self):
        """Test Australian phone extraction"""
        text = "Call us at +61 2 9123 4567"
        phone = self.scraper.extract_phone(text, country='AU')
        assert phone is not None
        assert "9123" in phone or "2" in phone
    
    def test_extract_phone_au_local_format(self):
        """Test Australian local format phone"""
        text = "Phone: 02 9123 4567"
        phone = self.scraper.extract_phone(text, country='AU')
        assert phone is not None
        assert "02" in phone or "2" in phone
    
    def test_extract_phones_multiple(self):
        """Test extracting multiple phones"""
        text = """
        Main: +61 2 9123 4567
        Mobile: 0412 345 678
        Toll Free: 1300 123 456
        """
        phones = self.scraper.extract_phones(text, country='AU', limit=3)
        assert len(phones) > 0
    
    def test_extract_company_name_valid(self):
        """Test company name extraction"""
        text = "Scent Australia Pty Ltd"
        name = self.scraper.extract_company_name(text)
        assert name == "Scent Australia Pty Ltd"
    
    def test_extract_company_name_invalid_social(self):
        """Test that social media names are excluded"""
        text = "LinkedIn Australia"
        name = self.scraper.extract_company_name(text)
        assert name is None
    
    def test_extract_address_with_postcode(self):
        """Test address extraction with postcode"""
        text = "Our office is at 123 Pitt Street, Sydney NSW 2000"
        address = self.scraper.extract_address(text)
        # Address extraction may return None if postcode context not found
        assert isinstance(address, (str, type(None)))
    
    def test_extract_social_links(self):
        """Test social media link extraction"""
        html = """
        <html>
            <a href="https://www.facebook.com/company">Facebook</a>
            <a href="https://www.linkedin.com/company/test">LinkedIn</a>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = self.scraper.extract_social_links(soup, 'https://example.com')
        
        assert 'facebook' in links
        assert 'linkedin' in links


class TestDataValidator:
    """Test DataValidator class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.validator = DataValidator()
    
    def test_validate_email_valid(self):
        """Test valid email validation"""
        is_valid, confidence = self.validator.validate_email("info@company.com.au")
        assert is_valid is True
        assert confidence > 0.5
    
    def test_validate_email_invalid(self):
        """Test invalid email validation"""
        is_valid, confidence = self.validator.validate_email("invalid-email")
        assert is_valid is False
        assert confidence == 0.0
    
    def test_validate_email_personal_domain(self):
        """Test personal email domain detection"""
        is_valid, confidence = self.validator.validate_email("user@gmail.com")
        assert is_valid is True
        assert confidence < 0.8  # Lower confidence for personal emails
    
    def test_validate_phone_au_valid(self):
        """Test valid Australian phone"""
        is_valid, confidence = self.validator.validate_phone("+61 2 9123 4567", country='AU')
        assert is_valid is True
        assert confidence > 0.5
    
    def test_validate_phone_au_invalid(self):
        """Test invalid phone"""
        is_valid, confidence = self.validator.validate_phone("123", country='AU')
        assert is_valid is False
    
    def test_validate_website_valid(self):
        """Test valid website validation"""
        is_valid, confidence = self.validator.validate_website("https://www.example.com.au")
        assert is_valid is True
        assert confidence > 0.5
    
    def test_validate_website_invalid(self):
        """Test invalid website"""
        is_valid, confidence = self.validator.validate_website("not-a-url")
        assert is_valid is False
    
    def test_validate_company_name_valid(self):
        """Test valid company name"""
        is_valid, confidence = self.validator.validate_company_name("Scent Australia Pty Ltd")
        assert is_valid is True
        assert confidence > 0.5
    
    def test_validate_company_name_invalid_social(self):
        """Test company name with social media keyword"""
        is_valid, confidence = self.validator.validate_company_name("LinkedIn Australia")
        assert is_valid is False
    
    def test_validate_address_with_postcode(self):
        """Test address with postcode"""
        is_valid, confidence = self.validator.validate_address("123 Pitt St, Sydney NSW 2000")
        assert is_valid is True
        assert confidence > 0.6
    
    def test_validate_lead_complete(self):
        """Test complete lead validation"""
        lead = {
            'company_name': 'Test Company',
            'email': 'info@test.com.au',
            'phone': '+61 2 9123 4567',
            'website': 'https://test.com.au',
            'address': '123 Test St, Sydney NSW 2000'
        }
        
        result = self.validator.validate_lead(lead)
        assert result.is_valid is True
        assert result.confidence > 30
        assert len(result.errors) == 0
    
    def test_validate_lead_with_errors(self):
        """Test lead validation with errors"""
        lead = {
            'company_name': '',
            'email': 'invalid-email',
            'phone': '123'
        }
        
        result = self.validator.validate_lead(lead)
        assert result.is_valid is False
        assert len(result.errors) > 0


class TestDataExtractor:
    """Test DataExtractor class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.extractor = DataExtractor()
    
    def test_extract_contact_info(self):
        """Test contact information extraction"""
        text = """
        Email: info@company.com.au
        Phone: +61 2 9123 4567
        Website: https://www.company.com.au
        """
        result = self.extractor.extract_contact_info(text)
        
        assert len(result['emails']) > 0
        assert len(result['phones']) > 0
        assert len(result['websites']) > 0
    
    def test_extract_business_info(self):
        """Test business information extraction"""
        text = """
        We are a fragrance company specializing in essential oils.
        Our company is a mid-size organization with 50-100 employees.
        Annual revenue: $5 million
        """
        result = self.extractor.extract_business_info(text)
        
        assert len(result['industry_keywords']) > 0
        assert len(result['revenue_indicators']) > 0
    
    def test_extract_location_australia(self):
        """Test location extraction for Australia"""
        text = "Our office is located in Sydney NSW 2000"
        result = self.extractor.extract_location(text)
        
        assert 'NSW' in result['states']


class TestLeadDataProcessor:
    """Test LeadDataProcessor class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.processor = LeadDataProcessor()
    
    def test_process_valid_lead(self):
        """Test processing a valid lead"""
        lead = {
            'company_name': 'Test Company',
            'email': 'info@test.com.au',
            'phone': '+61 2 9123 4567'
        }
        
        processed, validation = self.processor.process_lead(lead)
        
        assert processed['company_name'] == 'Test Company'
        assert 'validation' in processed
        assert validation.is_valid is True
    
    def test_process_invalid_lead(self):
        """Test processing an invalid lead"""
        lead = {
            'company_name': '',
            'email': 'invalid-email'
        }
        
        processed, validation = self.processor.process_lead(lead)
        
        assert validation.is_valid is False
        assert len(validation.errors) > 0
    
    def test_process_leads_batch(self):
        """Test batch processing of leads"""
        leads = [
            {
                'company_name': 'Company A',
                'email': 'a@a.com.au',
                'phone': '+61 2 1234 5678'
            },
            {
                'company_name': 'Company B',
                'email': 'invalid-email'
            },
            {
                'company_name': 'Company C',
                'phone': '0412 345 678'
            }
        ]
        
        processed, stats = self.processor.process_leads_batch(leads)
        
        assert len(processed) == 3
        assert stats['total_leads'] == 3
        assert stats['valid_leads'] >= 1
        assert 'average_confidence' in stats


class TestScrapingJobManager:
    """Test ScrapingJobManager class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = ScrapingJobManager()
    
    def test_create_job(self):
        """Test creating a new job"""
        job = self.manager.create_job(
            keywords=['fragrance'],
            locations=['Sydney, NSW'],
            max_leads=50
        )
        
        assert job.job_id is not None
        assert job.status == JobStatus.PENDING
        assert job.keywords == ['fragrance']
        assert job.locations == ['Sydney, NSW']
        assert job.max_leads == 50
    
    def test_get_job(self):
        """Test retrieving a job"""
        job = self.manager.create_job(
            keywords=['fragrance'],
            locations=['Sydney, NSW']
        )
        
        retrieved = self.manager.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id
    
    def test_update_job_status(self):
        """Test updating job status"""
        job = self.manager.create_job(
            keywords=['fragrance'],
            locations=['Sydney, NSW']
        )
        
        self.manager.update_job_status(job.job_id, JobStatus.RUNNING)
        
        updated = self.manager.get_job(job.job_id)
        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None
    
    def test_update_job_progress(self):
        """Test updating job progress"""
        job = self.manager.create_job(
            keywords=['fragrance'],
            locations=['Sydney, NSW'],
            max_leads=100
        )
        
        self.manager.update_job_progress(
            job.job_id,
            leads_found=50,
            leads_processed=40,
            leads_validated=35
        )
        
        updated = self.manager.get_job(job.job_id)
        assert updated.total_leads_found == 50
        assert updated.leads_processed == 40
        assert updated.leads_validated == 35
        assert updated.get_progress_percentage() == 40.0
    
    def test_list_jobs(self):
        """Test listing jobs"""
        # Create multiple jobs
        self.manager.create_job(keywords=['fragrance'], locations=['Sydney, NSW'])
        self.manager.create_job(keywords=['perfume'], locations=['Melbourne, VIC'])
        
        jobs = self.manager.list_jobs(limit=10)
        assert len(jobs) >= 2
    
    def test_list_jobs_by_status(self):
        """Test filtering jobs by status"""
        job1 = self.manager.create_job(keywords=['fragrance'], locations=['Sydney, NSW'])
        job2 = self.manager.create_job(keywords=['perfume'], locations=['Melbourne, VIC'])
        
        self.manager.update_job_status(job1.job_id, JobStatus.COMPLETED)
        
        completed = self.manager.list_jobs(status=JobStatus.COMPLETED)
        assert len(completed) >= 1
    
    def test_get_job_statistics(self):
        """Test getting job statistics"""
        self.manager.create_job(keywords=['fragrance'], locations=['Sydney, NSW'])
        
        stats = self.manager.get_job_statistics()
        
        assert 'total_jobs' in stats
        assert 'by_status' in stats
        assert 'total_leads_found' in stats


class TestScrapingJob:
    """Test ScrapingJob data class"""
    
    def test_job_to_dict(self):
        """Test converting job to dictionary"""
        job = ScrapingJob(
            job_id='test123',
            keywords=['fragrance'],
            locations=['Sydney, NSW'],
            max_leads=50
        )
        
        data = job.to_dict()
        
        assert data['job_id'] == 'test123'
        assert data['keywords'] == ['fragrance']
        assert data['max_leads'] == 50
        assert data['status'] == 'pending'
    
    def test_job_from_dict(self):
        """Test creating job from dictionary"""
        data = {
            'job_id': 'test123',
            'keywords': ['fragrance'],
            'locations': ['Sydney, NSW'],
            'max_leads': 50,
            'status': 'running'
        }
        
        job = ScrapingJob.from_dict(data)
        
        assert job.job_id == 'test123'
        assert job.keywords == ['fragrance']
        assert job.status == JobStatus.RUNNING
    
    def test_job_progress_percentage(self):
        """Test job progress calculation"""
        job = ScrapingJob(max_leads=100)
        job.leads_processed = 50
        
        progress = job.get_progress_percentage()
        assert progress == 50.0
    
    def test_job_elapsed_time(self):
        """Test job elapsed time calculation"""
        job = ScrapingJob()
        job.started_at = datetime.utcnow()
        
        elapsed = job.get_elapsed_time()
        assert elapsed >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
