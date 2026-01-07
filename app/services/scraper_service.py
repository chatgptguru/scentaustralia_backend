"""
Web Scraper Service
Handles web scraping for lead generation with anti-blocking measures and fallback sources
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from loguru import logger
import time
import re
import random
import json
from urllib.parse import urljoin, urlparse, quote_plus
from fake_useragent import UserAgent
from pathlib import Path
from datetime import datetime, timedelta

# Playwright for JavaScript rendering
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. JavaScript rendering will be unavailable.")

from app.config import Config


class ScraperService:
    """Service for web scraping lead information with anti-blocking and fallback measures"""
    
    # Browser user agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    # Common referrers to appear more legitimate
    REFERRERS = [
        'https://www.google.com/',
        'https://www.bing.com/',
        'https://duckduckgo.com/',
        'https://www.yahoo.com/',
    ]
    
    def __init__(self):
        """Initialize scraper service with retry strategy"""
        self.config = Config()
        self.ua = UserAgent(fallback='Mozilla/5.0')
        self.session = self._create_session()
        self.request_count = 0
        self.blocked_domains = {}  # Track blocked domains
        self.cache_dir = Path('scraper_cache')
        self.cache_dir.mkdir(exist_ok=True)
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy and connection pooling"""
        session = requests.Session()
        
        # Retry strategy for handling rate limiting and temporary failures
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1  # Will wait 1, 2, 4 seconds between retries
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        self._update_session_headers(session)
        return session
    
    def _update_session_headers(self, session: requests.Session):
        """Update session headers with random user agent and referrer"""
        user_agent = random.choice(self.USER_AGENTS) if random.random() > 0.3 else self.ua.random
        
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,en-AU;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': random.choice(self.REFERRERS),
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })
    
    def _is_blocked(self, domain: str) -> bool:
        """Check if domain is currently blocked"""
        if domain not in self.blocked_domains:
            return False
        
        block_time, count = self.blocked_domains[domain]
        
        # Unblock after 30 minutes + (count * 10) minutes
        unblock_after = block_time + timedelta(minutes=30 + (count * 10))
        
        if datetime.now() > unblock_after:
            del self.blocked_domains[domain]
            logger.info(f"Domain {domain} unblocked")
            return False
        
        return True
    
    def _mark_blocked(self, domain: str):
        """Mark domain as blocked"""
        if domain in self.blocked_domains:
            block_time, count = self.blocked_domains[domain]
            self.blocked_domains[domain] = (block_time, count + 1)
        else:
            self.blocked_domains[domain] = (datetime.now(), 1)
        
        logger.warning(f"Domain {domain} marked as blocked (attempts: {self.blocked_domains[domain][1]})")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return str(hash(url)) + '.json'
    
    def _get_cached_response(self, url: str) -> Optional[BeautifulSoup]:
        """Get cached response if available and not expired"""
        try:
            cache_file = self.cache_dir / self._get_cache_key(url)
            if not cache_file.exists():
                return None
            
            # Check if cache is less than 24 hours old
            if (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).seconds > 86400:
                cache_file.unlink()
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                html = json.load(f).get('html', '')
            
            logger.debug(f"Using cached response for {url}")
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            logger.debug(f"Cache read error: {str(e)}")
            return None
    
    def _cache_response(self, url: str, html: str):
        """Cache HTML response"""
        try:
            cache_file = self.cache_dir / self._get_cache_key(url)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'html': html, 'cached_at': str(datetime.now())}, f)
        except Exception as e:
            logger.warning(f"Cache write error: {str(e)}")
    
    def _make_request(self, url: str, retries: int = 3, use_cache: bool = True) -> Optional[BeautifulSoup]:
        """Make HTTP request with retries, rate limiting, and caching"""
        domain = urlparse(url).netloc
        
        # Check if domain is blocked
        if self._is_blocked(domain):
            logger.warning(f"Domain {domain} is currently blocked, using cached data")
            return self._get_cached_response(url)
        
        # Try to get from cache first
        if use_cache:
            cached = self._get_cached_response(url)
            if cached:
                return cached
        
        for attempt in range(retries):
            try:
                # Update headers for each request
                self._update_session_headers(self.session)
                
                # Variable delay based on request count
                base_delay = self.config.SCRAPING_DELAY + random.uniform(1, 3)
                if self.request_count > 10:
                    base_delay *= 2  # Increase delay after many requests
                
                time.sleep(base_delay)
                self.request_count += 1
                
                response = self.session.get(
                    url,
                    timeout=self.config.REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                
                # Handle specific error codes
                if response.status_code == 403:
                    self._mark_blocked(domain)
                    logger.warning(f"Access forbidden (403) to {domain}, trying alternative sources")
                    return None
                
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited (429) by {domain}, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    self._mark_blocked(domain)
                    return None
                
                response.raise_for_status()
                
                # Ensure proper text encoding (handles gzip automatically)
                text = response.text
                
                # Cache successful response
                self._cache_response(url, text)
                
                return BeautifulSoup(response.text, 'html.parser')
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)[:100]}")
                
                if attempt < retries - 1:
                    backoff_time = 2 ** attempt + random.uniform(0, 1)
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    self._mark_blocked(domain)
        
        return None
    
    def _make_request_with_playwright(self, url: str, wait_selector: str = None) -> Optional[BeautifulSoup]:
        """
        Make HTTP request using Playwright to render JavaScript-heavy pages.
        Falls back to regular requests if Playwright is unavailable.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning(f"Playwright not available, using regular request for: {url}")
            return self._make_request(url)
        
        try:
            logger.debug(f"Using Playwright to fetch: {url}")
            
            with sync_playwright() as p:
                # Use Chromium for better performance
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=random.choice(self.USER_AGENTS),
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = context.new_page()
                
                # Set referrer
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for specific element if provided
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=5000)
                    except:
                        logger.debug(f"Selector {wait_selector} not found, proceeding anyway")
                
                # Get rendered HTML
                html = page.content()
                
                # Cache the response
                self._cache_response(url, html)
                
                context.close()
                browser.close()
                
                logger.debug(f"Playwright successfully fetched {len(html)} bytes from {url}")
                return BeautifulSoup(html, 'html.parser')
                
        except Exception as e:
            logger.error(f"Playwright error for {url}: {str(e)[:100]}")
            # Fallback to regular request
            return self._make_request(url)
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text)
        
        # Filter out common non-business emails
        excluded_domains = ['example.com', 'test.com', 'email.com', 'domain.com']
        for match in matches:
            if not any(domain in match.lower() for domain in excluded_domains):
                return match.lower()
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract Australian phone number from text"""
        # Australian phone patterns
        patterns = [
            r'\+61\s*[2-9]\s*\d{4}\s*\d{4}',  # +61 X XXXX XXXX
            r'0[2-9]\s*\d{4}\s*\d{4}',         # 0X XXXX XXXX
            r'\(0[2-9]\)\s*\d{4}\s*\d{4}',     # (0X) XXXX XXXX
            r'1[38]00\s*\d{3}\s*\d{3}',        # 1300/1800 XXX XXX
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean and return first match
                phone = re.sub(r'\s+', ' ', matches[0])
                return phone
        
        return None
    
    def _extract_website(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract website URL from page"""
        # Look for website links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            if 'website' in text or 'visit' in text:
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    return urljoin(base_url, href)
        
        return None
    
    def scrape_all_sources(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape from all available sources with graceful fallback"""
        all_leads = []
        sources_attempted = 0
        
        # Priority order: most reliable first
        sources = [
            ('business_directories', lambda: self.scrape_business_directories(keywords, locations, max_results)),
            ('linkedin', lambda: self.scrape_linkedin(keywords, locations, max_results // 2)),
            ('google_maps', lambda: self.scrape_google_maps(keywords, locations, max_results)),
            ('yellow_pages', lambda: self.scrape_yellow_pages(keywords, locations, max_results // 2)),
        ]
        
        for source_name, scrape_fn in sources:
            try:
                if len(all_leads) >= max_results:
                    break
                
                logger.info(f"Trying source: {source_name}")
                leads = scrape_fn()
                sources_attempted += 1
                
                if leads:
                    all_leads.extend(leads)
                    logger.info(f"{source_name}: Found {len(leads)} leads")
                else:
                    logger.warning(f"{source_name}: No leads found, trying next source")
                    
            except Exception as e:
                logger.error(f"Error with {source_name}: {str(e)}, trying next source")
                sources_attempted += 1
                continue
        
        # Deduplicate by company name
        unique_leads = {}
        for lead in all_leads:
            key = lead.get('company_name', '').lower()
            if key and key not in unique_leads:
                unique_leads[key] = lead
        
        result = list(unique_leads.values())[:max_results]
        logger.info(f"All sources completed. Found {len(result)} unique leads.")
        return result
    
    def scrape_google_search(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """
        Google Search scraping - Currently not functional due to bot detection.
        Web scraping without a paid API is not viable in 2026.
        
        Recommended solutions:
        1. Use Brave Search API (free tier: 2000/month)
        2. Use Google Places API (free tier: 150/day)
        3. Use Hunter.io (find emails by domain)
        4. Use Australian Business Register (free, no API needed)
        
        See FREE_SOLUTIONS.md for details.
        """
        logger.warning("Google Search scraping requires a paid API. See FREE_SOLUTIONS.md for alternatives.")
        return []
    
    def scrape_google_maps(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape business information from Google Maps"""
        
        leads = []
        results_per_query = max(5, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # Google Maps URL (note: direct scraping is limited, but we try)
                    search_query = f"{keyword} {location}"
                    maps_url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"
                    
                    logger.info(f"Scraping Google Maps for: {keyword} in {location}")
                    
                    soup = self._make_request(maps_url, retries=2, use_cache=False)
                    if not soup:
                        logger.debug(f"Google Maps blocked, skipping {keyword}")
                        continue
                    
                    # Extract business listings
                    listings = soup.find_all('div', class_='Nv2PK')[:results_per_query]
                    
                    for listing in listings:
                        try:
                            # Extract business name
                            name_elem = listing.find('div', class_='B6MsF')
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            if not company_name:
                                continue
                            
                            # Try to extract phone from rating section
                            rating_section = listing.find('div', class_='RgQvf')
                            phone = None
                            if rating_section:
                                phone_match = re.search(r'[\d\s\-\(\)]{10,}', rating_section.get_text())
                                if phone_match:
                                    phone = self._extract_phone(rating_section.get_text())
                            
                            lead_data = {
                                'company_name': company_name,
                                'phone': phone,
                                'location': location,
                                'industry': keyword,
                                'source': 'google-maps',
                                'source_url': maps_url
                            }
                            
                            leads.append(lead_data)
                            logger.debug(f"Found lead from Maps: {company_name}")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing Maps listing: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.warning(f"Error scraping Google Maps: {str(e)}")
                    continue
        
        logger.info(f"Google Maps scraping completed. Found {len(leads)} leads.")
        return leads[:max_results]
    
    def scrape_linkedin(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape company information from LinkedIn (limited - LinkedIn blocks bots)"""
        
        leads = []
        logger.warning("LinkedIn scraping: Limited functionality due to bot detection")
        
        # Note: LinkedIn has strong anti-scraping measures
        # This is a fallback method with low success rate
        for keyword in keywords[:1]:  # Limit to avoid blocks
            for location in locations[:1]:
                try:
                    linkedin_url = f"https://www.linkedin.com/search/results/companies/?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
                    
                    logger.info(f"Attempting LinkedIn search for: {keyword} in {location}")
                    
                    soup = self._make_request(linkedin_url, retries=2, use_cache=False)
                    if not soup:
                        logger.warning("LinkedIn likely blocked bot request")
                        break
                    
                    # LinkedIn structure is complex and changes frequently
                    # Extract what we can
                    company_names = soup.find_all('span', class_='dist-value')
                    
                    for i, name_elem in enumerate(company_names[:max_results // 2]):
                        try:
                            company_name = name_elem.get_text().strip()
                            if company_name and len(company_name) > 2:
                                lead_data = {
                                    'company_name': company_name,
                                    'location': location,
                                    'industry': keyword,
                                    'source': 'linkedin',
                                    'source_url': linkedin_url
                                }
                                leads.append(lead_data)
                        except Exception as e:
                            continue
                    
                except Exception as e:
                    logger.warning(f"LinkedIn scraping failed: {str(e)}")
                    break
        
        logger.info(f"LinkedIn scraping completed. Found {len(leads)} leads.")
        return leads
    
    def scrape_yellow_pages(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape business listings from Yellow Pages Australia with fallback"""
        
        leads = []
        results_per_query = max(5, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                # Check if Yellow Pages is blocked
                if self._is_blocked('yellowpages.com.au'):
                    logger.warning("Yellow Pages is currently blocked, skipping")
                    continue
                
                try:
                    # Build Yellow Pages URL
                    url = f"https://www.yellowpages.com.au/search/listings?clue={quote_plus(keyword)}&locationClue={quote_plus(location)}"
                    
                    logger.info(f"Scraping Yellow Pages for: {keyword} in {location}")
                    
                    soup = self._make_request(url, retries=2)
                    if not soup:
                        logger.debug("Yellow Pages request failed, data might be cached or blocked")
                        continue
                    
                    # Parse listings with multiple selector attempts
                    listings = soup.find_all('div', class_='listing')
                    if not listings:
                        listings = soup.find_all('div', class_='search-result')
                    
                    listings = listings[:results_per_query]
                    
                    for listing in listings:
                        try:
                            # Extract business name with fallback selectors
                            name_elem = listing.find('a', class_='listing-name')
                            if not name_elem:
                                name_elem = listing.find('h3')
                            
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            if not company_name:
                                continue
                            
                            # Extract contact info
                            phone_elem = listing.find('a', class_='click-to-call')
                            if not phone_elem:
                                phone_elem = listing.find('span', class_='phone')
                            
                            phone = phone_elem.get_text().strip() if phone_elem else None
                            
                            # Extract address
                            address_elem = listing.find('p', class_='listing-address')
                            if not address_elem:
                                address_elem = listing.find('div', class_='address')
                            
                            address = address_elem.get_text().strip() if address_elem else None
                            
                            # Extract website
                            website_elem = listing.find('a', class_='contact-url')
                            if not website_elem:
                                website_elem = listing.find('a', {'href': re.compile(r'http.*')})
                            
                            website = website_elem['href'] if website_elem and website_elem.get('href') else None
                            
                            lead_data = {
                                'company_name': company_name,
                                'phone': phone,
                                'address': address,
                                'website': website,
                                'industry': keyword,
                                'location': location,
                                'source': 'yellow-pages',
                                'source_url': url
                            }
                            
                            leads.append(lead_data)
                            logger.debug(f"Found lead: {company_name}")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing Yellow Pages listing: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error scraping Yellow Pages for {keyword} in {location}: {str(e)}")
                    continue
        
        logger.info(f"Yellow Pages scraping completed. Found {len(leads)} leads.")
        return leads[:max_results]
    
    def scrape_business_directories(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape from multiple business directories with fallback"""
        
        leads = []
        results_per_source = max_results // 3
        
        # Try multiple sources
        sources = [
            ('True Local', lambda: self._scrape_truelocal(keywords, locations, results_per_source)),
            ('Hotfrog', lambda: self._scrape_hotfrog(keywords, locations, results_per_source)),
            ('Brownbook', lambda: self._scrape_brownbook(keywords, locations, results_per_source)),
        ]
        
        for source_name, scrape_fn in sources:
            try:
                if len(leads) >= max_results:
                    break
                
                logger.info(f"Trying {source_name}...")
                source_leads = scrape_fn()
                
                if source_leads:
                    leads.extend(source_leads)
                    logger.info(f"{source_name}: Found {len(source_leads)} leads")
                
            except Exception as e:
                logger.warning(f"Error with {source_name}: {str(e)}, continuing...")
                continue
        
        logger.info(f"Business directory scraping completed. Found {len(leads)} leads.")
        return leads[:max_results]
    
    def _scrape_hotfrog(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int
    ) -> List[Dict]:
        """Scrape from Hotfrog Australia"""
        
        leads = []
        results_per_query = max(3, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    url = f"https://www.hotfrog.com.au/search/{quote_plus(location)}/{quote_plus(keyword)}"
                    
                    logger.debug(f"Scraping Hotfrog: {keyword} in {location}")
                    
                    soup = self._make_request(url, retries=2)
                    if not soup:
                        continue
                    
                    # Try multiple selector patterns for Hotfrog
                    listings = soup.find_all('div', class_='listing-item')
                    if not listings:
                        listings = soup.find_all('div', class_='business-listing')
                    
                    for listing in listings[:results_per_query]:
                        try:
                            name_elem = listing.find('a', class_='listing-title')
                            if not name_elem:
                                name_elem = listing.find('h2')
                            
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            if not company_name or len(company_name) < 2:
                                continue
                            
                            lead_data = {
                                'company_name': company_name,
                                'industry': keyword,
                                'location': location,
                                'source': 'hotfrog',
                                'source_url': url
                            }
                            
                            # Try to extract phone
                            phone_elem = listing.find('span', class_='phone')
                            if not phone_elem:
                                phone_elem = listing.find('a', {'href': re.compile(r'tel:')})
                            
                            if phone_elem:
                                phone_text = phone_elem.get_text().strip()
                                lead_data['phone'] = phone_text
                            
                            # Try to extract website
                            website_elem = listing.find('a', {'href': re.compile(r'http.*')})
                            if website_elem:
                                lead_data['website'] = website_elem['href']
                            
                            leads.append(lead_data)
                            logger.debug(f"Hotfrog: Found {company_name}")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing Hotfrog listing: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.warning(f"Error scraping Hotfrog: {str(e)}")
        
        return leads
    
    def _scrape_truelocal(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int
    ) -> List[Dict]:
        """Scrape from TrueLocal"""
        
        leads = []
        results_per_query = max(3, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # TrueLocal uses different URL structure
                    location_slug = location.replace(', ', '/').replace(' ', '-').lower()
                    url = f"https://www.truelocal.com.au/search/{quote_plus(keyword)}/{location_slug}"
                    
                    logger.debug(f"Scraping TrueLocal: {keyword} in {location}")
                    
                    soup = self._make_request(url, retries=2)
                    if not soup:
                        continue
                    
                    # Try multiple selector patterns
                    listings = soup.find_all('div', class_='search-result')
                    if not listings:
                        listings = soup.find_all('article', class_='business')
                    
                    for listing in listings[:results_per_query]:
                        try:
                            name_elem = listing.find('h3', class_='name')
                            if not name_elem:
                                name_elem = listing.find('h2')
                            
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            if not company_name or len(company_name) < 2:
                                continue
                            
                            lead_data = {
                                'company_name': company_name,
                                'industry': keyword,
                                'location': location,
                                'source': 'truelocal',
                                'source_url': url
                            }
                            
                            # Extract phone if available
                            phone_elem = listing.find('span', class_='phone')
                            if phone_elem:
                                lead_data['phone'] = phone_elem.get_text().strip()
                            
                            # Extract address if available
                            address_elem = listing.find('div', class_='address')
                            if address_elem:
                                lead_data['address'] = address_elem.get_text().strip()
                            
                            # Extract website if available
                            website_elem = listing.find('a', {'href': re.compile(r'http.*')})
                            if website_elem:
                                lead_data['website'] = website_elem['href']
                            
                            leads.append(lead_data)
                            logger.debug(f"TrueLocal: Found {company_name}")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing TrueLocal listing: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.warning(f"Error scraping TrueLocal: {str(e)}")
        
        return leads
    
    def _scrape_brownbook(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int
    ) -> List[Dict]:
        """Scrape from Brownbook (Australian business directory)"""
        
        leads = []
        results_per_query = max(3, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # Brownbook URL structure
                    url = f"https://www.brownbook.net/search.php?q={quote_plus(keyword)}&l={quote_plus(location)}"
                    
                    logger.debug(f"Scraping Brownbook: {keyword} in {location}")
                    
                    soup = self._make_request(url, retries=2)
                    if not soup:
                        continue
                    
                    # Parse Brownbook listings
                    listings = soup.find_all('div', class_='result')
                    if not listings:
                        listings = soup.find_all('div', class_='listing')
                    
                    for listing in listings[:results_per_query]:
                        try:
                            # Extract business name
                            name_elem = listing.find('h2')
                            if not name_elem:
                                name_elem = listing.find('a', class_='business-name')
                            
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            if not company_name or len(company_name) < 2:
                                continue
                            
                            lead_data = {
                                'company_name': company_name,
                                'industry': keyword,
                                'location': location,
                                'source': 'brownbook',
                                'source_url': url
                            }
                            
                            # Extract phone
                            phone_text = listing.get_text()
                            phone = self._extract_phone(phone_text)
                            if phone:
                                lead_data['phone'] = phone
                            
                            # Extract email
                            email = self._extract_email(phone_text)
                            if email:
                                lead_data['email'] = email
                            
                            # Extract website link
                            website_elem = listing.find('a', {'href': re.compile(r'http.*')})
                            if website_elem:
                                lead_data['website'] = website_elem['href']
                            
                            leads.append(lead_data)
                            logger.debug(f"Brownbook: Found {company_name}")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing Brownbook listing: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.warning(f"Error scraping Brownbook: {str(e)}")
        
        return leads
    
    def scrape_company_website(self, url: str) -> Dict:
        """Scrape detailed information from a company's website"""
        
        result = {
            'website': url,
            'email': None,
            'phone': None,
            'address': None,
            'social_links': []
        }
        
        try:
            soup = self._make_request(url)
            if not soup:
                return result
            
            # Get all text content
            text = soup.get_text()
            
            # Extract email
            result['email'] = self._extract_email(text)
            
            # Extract phone
            result['phone'] = self._extract_phone(text)
            
            # Look for contact page
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                if 'contact' in href:
                    contact_url = urljoin(url, link['href'])
                    contact_soup = self._make_request(contact_url)
                    if contact_soup:
                        contact_text = contact_soup.get_text()
                        if not result['email']:
                            result['email'] = self._extract_email(contact_text)
                        if not result['phone']:
                            result['phone'] = self._extract_phone(contact_text)
                    break
            
            # Extract social media links
            social_patterns = ['facebook', 'linkedin', 'twitter', 'instagram']
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                for social in social_patterns:
                    if social in href and href not in result['social_links']:
                        result['social_links'].append(href)
            
        except Exception as e:
            logger.error(f"Error scraping company website {url}: {str(e)}")
        
        return result

