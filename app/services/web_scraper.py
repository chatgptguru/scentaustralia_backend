"""
Advanced Web Scraping Module
Handles intelligent web scraping for lead generation with multiple data extraction methods
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse, quote_plus
from loguru import logger
import time
import re
import random
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from fake_useragent import UserAgent
import json

from app.config import Config


class WebScraper:
    """Advanced web scraper for lead generation"""
    
    def __init__(self, use_selenium: bool = False):
        """
        Initialize web scraper
        
        Args:
            use_selenium: Use Selenium for JavaScript-heavy sites
        """
        self.config = Config()
        self.ua = UserAgent()
        self.session = self._setup_session()
        self.use_selenium = use_selenium
        self.driver = None
        
        # Email patterns and validation
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        
        # Phone patterns for different countries
        self.phone_patterns = {
            'AU': [
                r'\+61\s*[2-9]\s*\d{4}\s*\d{4}',
                r'0[2-9]\s*\d{4}\s*\d{4}',
                r'\(0[2-9]\)\s*\d{4}\s*\d{4}',
                r'1[38]00\s*\d{3}\s*\d{3}',
            ],
            'US': [
                r'\+1\s*\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            ]
        }
        
        # Common non-business email domains to exclude
        self.excluded_email_domains = {
            'example.com', 'test.com', 'email.com', 'domain.com',
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'mail.com', 'aol.com'
        }
        
        # Common non-business words in company names
        self.exclude_keywords = {
            'linkedin', 'facebook', 'yelp', 'wikipedia', 'indeed',
            'glassdoor', 'twitter', 'instagram', 'youtube', 'pinterest'
        }
    
    def _setup_session(self) -> requests.Session:
        """Setup requests session with headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-AU,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
        })
        return session
    
    def _setup_selenium_driver(self) -> webdriver.Chrome:
        """Setup Selenium WebDriver for JavaScript-heavy sites"""
        if self.driver:
            return self.driver
        
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'user-agent={self.ua.random}')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {str(e)}")
            return None
    
    def close_driver(self):
        """Close Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {str(e)}")
    
    def fetch_page(self, url: str, use_selenium: bool = False, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page
        
        Args:
            url: URL to fetch
            use_selenium: Use Selenium for JavaScript rendering
            retries: Number of retries on failure
        
        Returns:
            BeautifulSoup object or None
        """
        for attempt in range(retries):
            try:
                # Add random delay to avoid rate limiting
                time.sleep(self.config.SCRAPING_DELAY + random.uniform(0.5, 2.0))
                
                # Update user agent
                self.session.headers['User-Agent'] = self.ua.random
                
                if use_selenium and self.use_selenium:
                    return self._fetch_with_selenium(url)
                else:
                    return self._fetch_with_requests(url)
                    
            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None
    
    def _fetch_with_requests(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page using requests library"""
        try:
            response = self.session.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.debug(f"Requests fetch failed for {url}: {str(e)}")
            return None
    
    def _fetch_with_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page using Selenium for JavaScript rendering"""
        try:
            driver = self._setup_selenium_driver()
            if not driver:
                return None
            
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # Wait for dynamic content
            return BeautifulSoup(driver.page_source, 'html.parser')
            
        except Exception as e:
            logger.debug(f"Selenium fetch failed for {url}: {str(e)}")
            return None
    
    def extract_email(self, text: str) -> Optional[str]:
        """
        Extract and validate email from text
        
        Args:
            text: Text to extract email from
        
        Returns:
            Valid email address or None
        """
        emails = self.email_pattern.findall(text)
        
        for email in emails:
            email_lower = email.lower()
            
            # Skip if domain is in excluded list
            domain = email_lower.split('@')[1]
            if domain in self.excluded_email_domains:
                continue
            
            # Validate email format
            try:
                validate_email(email_lower, check_deliverability=False)
                return email_lower
            except EmailNotValidError:
                continue
        
        return None
    
    def extract_emails(self, text: str, limit: int = 5) -> List[str]:
        """Extract multiple valid emails from text"""
        emails = []
        found_emails = self.email_pattern.findall(text)
        
        for email in found_emails:
            if len(emails) >= limit:
                break
            
            email_lower = email.lower()
            domain = email_lower.split('@')[1]
            
            if domain in self.excluded_email_domains:
                continue
            
            try:
                validate_email(email_lower, check_deliverability=False)
                if email_lower not in emails:
                    emails.append(email_lower)
            except EmailNotValidError:
                continue
        
        return emails
    
    def extract_phone(self, text: str, country: str = 'AU') -> Optional[str]:
        """
        Extract phone number from text
        
        Args:
            text: Text to extract phone from
            country: Country code (AU, US, etc.)
        
        Returns:
            Phone number or None
        """
        patterns = self.phone_patterns.get(country, self.phone_patterns['AU'])
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                phone = re.sub(r'\s+', ' ', matches[0])
                return phone.strip()
        
        return None
    
    def extract_phones(self, text: str, country: str = 'AU', limit: int = 3) -> List[str]:
        """Extract multiple phone numbers from text"""
        phones = []
        patterns = self.phone_patterns.get(country, self.phone_patterns['AU'])
        
        for pattern in patterns:
            if len(phones) >= limit:
                break
            
            matches = re.findall(pattern, text)
            for match in matches:
                if len(phones) >= limit:
                    break
                
                phone = re.sub(r'\s+', ' ', match).strip()
                if phone not in phones:
                    phones.append(phone)
        
        return phones
    
    def extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[str]]:
        """
        Extract social media links from page
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for relative link resolution
        
        Returns:
            Dictionary with social media links
        """
        social_links = {
            'facebook': [],
            'linkedin': [],
            'twitter': [],
            'instagram': [],
            'youtube': [],
            'tiktok': [],
            'pinterest': []
        }
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            
            for platform, platform_list in social_links.items():
                if platform in href and href not in platform_list:
                    if href.startswith('http'):
                        platform_list.append(href)
                    elif href.startswith('/'):
                        full_url = urljoin(base_url, href)
                        if full_url not in platform_list:
                            platform_list.append(full_url)
        
        return {k: v for k, v in social_links.items() if v}
    
    def extract_company_name(self, text: str) -> Optional[str]:
        """
        Extract company name from text
        
        Args:
            text: Text to extract from
        
        Returns:
            Company name or None
        """
        # Remove common non-business keywords
        text_lower = text.lower()
        for keyword in self.exclude_keywords:
            if keyword in text_lower:
                return None
        
        # Clean and validate
        name = text.strip()
        
        # Exclude if too short or contains common non-business patterns
        if len(name) < 2 or len(name) > 100:
            return None
        
        # Check for common business indicators
        business_words = ['company', 'inc', 'ltd', 'pty', 'group', 'services', 'solutions']
        if any(word in name.lower() for word in business_words):
            return name
        
        # If contains numbers or common company chars, likely valid
        if any(char in name for char in ['&', '-', '(', ')']):
            return name
        
        # Basic check for multiple words
        if len(name.split()) >= 2:
            return name
        
        return None
    
    def extract_address(self, text: str) -> Optional[str]:
        """
        Extract address from text
        
        Args:
            text: Text to extract from
        
        Returns:
            Address or None
        """
        # Australian postcode pattern
        postcode_pattern = r'\b[0-9]{4}\s+[A-Z]{2,}\b'
        
        # Look for postcode
        postcodes = re.findall(postcode_pattern, text)
        if postcodes:
            # Get surrounding text
            for postcode in postcodes:
                idx = text.find(postcode)
                if idx > 0:
                    # Get up to 200 chars before postcode
                    start = max(0, idx - 200)
                    address_chunk = text[start:idx + len(postcode)]
                    # Find the last newline or period
                    last_break = max(address_chunk.rfind('\n'), address_chunk.rfind('.'))
                    if last_break > 0:
                        address = address_chunk[last_break + 1:].strip()
                    else:
                        address = address_chunk.strip()
                    
                    if len(address) > 5:
                        return address
        
        return None
    
    def extract_all_text(self, soup: BeautifulSoup, remove_scripts: bool = True) -> str:
        """
        Extract all text from page
        
        Args:
            soup: BeautifulSoup object
            remove_scripts: Remove script and style tags
        
        Returns:
            Cleaned text content
        """
        if remove_scripts:
            for script in soup(['script', 'style']):
                script.decompose()
        
        text = soup.get_text()
        
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def scrape_business_listing(self, url: str) -> Dict:
        """
        Scrape complete business information from a listing URL
        
        Args:
            url: URL of business listing
        
        Returns:
            Dictionary with extracted information
        """
        result = {
            'url': url,
            'company_name': None,
            'emails': [],
            'phones': [],
            'address': None,
            'social_links': {},
            'website': None,
            'raw_text': '',
            'scraped_at': datetime.utcnow().isoformat()
        }
        
        try:
            soup = self.fetch_page(url)
            if not soup:
                return result
            
            # Extract all text
            text = self.extract_all_text(soup)
            result['raw_text'] = text[:5000]  # Store first 5000 chars
            
            # Extract company name from title or header
            title = soup.find('title')
            if title:
                name = self.extract_company_name(title.get_text())
                if name:
                    result['company_name'] = name
            
            if not result['company_name']:
                h1 = soup.find('h1')
                if h1:
                    name = self.extract_company_name(h1.get_text())
                    if name:
                        result['company_name'] = name
            
            # Extract contact information
            result['emails'] = self.extract_emails(text)
            result['phones'] = self.extract_phones(text)
            result['address'] = self.extract_address(text)
            
            # Extract social links
            result['social_links'] = self.extract_social_links(soup, url)
            
            # Extract website if available
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text_content = link.get_text().lower()
                
                if ('website' in text_content or 'visit' in text_content) and href.startswith('http'):
                    result['website'] = href
                    break
            
            logger.debug(f"Successfully scraped: {url}")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
        
        return result
    
    def scrape_directory_listings(
        self,
        search_url: str,
        selector: Dict[str, str],
        max_results: int = 50
    ) -> List[Dict]:
        """
        Scrape business listings from a directory
        
        Args:
            search_url: URL of search results page
            selector: CSS selectors for parsing (name, email, phone, address, url)
            max_results: Maximum results to scrape
        
        Returns:
            List of lead dictionaries
        """
        leads = []
        
        try:
            soup = self.fetch_page(search_url)
            if not soup:
                return leads
            
            # Find all listing containers
            listings = soup.find_all('div', class_=selector.get('container', 'listing'))
            
            for listing in listings[:max_results]:
                try:
                    lead = {}
                    
                    # Extract company name
                    if 'name' in selector:
                        name_elem = listing.find(selector['name']['tag'], class_=selector['name'].get('class'))
                        if name_elem:
                            lead['company_name'] = name_elem.get_text().strip()
                    
                    # Extract email
                    if 'email' in selector:
                        email_elem = listing.find(selector['email']['tag'], class_=selector['email'].get('class'))
                        if email_elem:
                            email_text = email_elem.get_text()
                            email = self.extract_email(email_text)
                            if email:
                                lead['email'] = email
                    
                    # Extract phone
                    if 'phone' in selector:
                        phone_elem = listing.find(selector['phone']['tag'], class_=selector['phone'].get('class'))
                        if phone_elem:
                            phone_text = phone_elem.get_text()
                            phone = self.extract_phone(phone_text)
                            if phone:
                                lead['phone'] = phone
                    
                    # Extract address
                    if 'address' in selector:
                        address_elem = listing.find(selector['address']['tag'], class_=selector['address'].get('class'))
                        if address_elem:
                            lead['address'] = address_elem.get_text().strip()
                    
                    # Extract URL
                    if 'url' in selector:
                        url_elem = listing.find('a', href=True)
                        if url_elem:
                            lead['website'] = url_elem.get('href')
                    
                    # Only add if has at least company name
                    if 'company_name' in lead:
                        lead['source_url'] = search_url
                        leads.append(lead)
                
                except Exception as e:
                    logger.warning(f"Error parsing listing: {str(e)}")
                    continue
            
            logger.info(f"Scraped {len(leads)} listings from directory")
            
        except Exception as e:
            logger.error(f"Error scraping directory {search_url}: {str(e)}")
        
        return leads
    
    def search_and_scrape(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50,
        search_engine: str = 'google'
    ) -> List[Dict]:
        """
        Search and scrape business information based on keywords and locations
        
        Args:
            keywords: List of keywords to search
            locations: List of locations to search in
            max_results: Maximum results to return
            search_engine: Search engine to use (google, bing, etc.)
        
        Returns:
            List of leads
        """
        leads = []
        results_per_query = max(3, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            if len(leads) >= max_results:
                break
            
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # Build search query
                    query = f"{keyword} business contact {location}"
                    
                    if search_engine.lower() == 'google':
                        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={results_per_query}"
                    elif search_engine.lower() == 'bing':
                        search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={results_per_query}"
                    else:
                        continue
                    
                    logger.info(f"Searching: {keyword} in {location}")
                    
                    soup = self.fetch_page(search_url)
                    if not soup:
                        continue
                    
                    # Parse search results (simplified for Google)
                    for result in soup.find_all('div', class_='g')[:results_per_query]:
                        try:
                            title_elem = result.find('h3')
                            if not title_elem:
                                continue
                            
                            company_name = title_elem.get_text().strip()
                            
                            # Skip non-business results
                            if any(skip in company_name.lower() for skip in self.exclude_keywords):
                                continue
                            
                            # Extract URL
                            link = result.find('a', href=True)
                            website = link['href'] if link else None
                            
                            # Extract snippet
                            snippet_elem = result.find('span', class_='aCOpRe')
                            snippet = snippet_elem.get_text() if snippet_elem else ''
                            
                            lead = {
                                'company_name': company_name,
                                'website': website,
                                'email': self.extract_email(snippet),
                                'phone': self.extract_phone(snippet),
                                'industry': keyword,
                                'location': location,
                                'source': 'search-engine',
                                'source_url': search_url,
                                'scraped_at': datetime.utcnow().isoformat()
                            }
                            
                            # Only add if has company name
                            if lead['company_name']:
                                leads.append(lead)
                                logger.debug(f"Found: {company_name}")
                        
                        except Exception as e:
                            logger.debug(f"Error parsing result: {str(e)}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error searching for {keyword} in {location}: {str(e)}")
                    continue
        
        logger.info(f"Search and scrape completed. Found {len(leads)} leads")
        return leads[:max_results]


# Convenience function for backward compatibility
def scrape_business_info(url: str, use_selenium: bool = False) -> Dict:
    """
    Scrape business information from a URL
    
    Args:
        url: URL to scrape
        use_selenium: Use Selenium for JavaScript-heavy sites
    
    Returns:
        Dictionary with extracted information
    """
    scraper = WebScraper(use_selenium=use_selenium)
    try:
        result = scraper.scrape_business_listing(url)
        return result
    finally:
        scraper.close_driver()
