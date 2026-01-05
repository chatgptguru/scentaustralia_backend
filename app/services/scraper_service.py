"""
Web Scraper Service
Handles web scraping for lead generation
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from loguru import logger
import time
import re
import random
from urllib.parse import urljoin, urlparse, quote_plus
from fake_useragent import UserAgent

from app.config import Config


class ScraperService:
    """Service for web scraping lead information"""
    
    def __init__(self):
        """Initialize scraper service"""
        self.config = Config()
        self.ua = UserAgent()
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup requests session with headers"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Make HTTP request with retries and error handling"""
        for attempt in range(retries):
            try:
                # Update user agent for each request
                self.session.headers['User-Agent'] = self.ua.random
                
                # Add delay to avoid rate limiting
                time.sleep(self.config.SCRAPING_DELAY + random.uniform(0.5, 1.5))
                
                response = self.session.get(
                    url,
                    timeout=self.config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                
                return BeautifulSoup(response.text, 'lxml')
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt == retries - 1:
                    logger.error(f"Failed to fetch {url}: {str(e)}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
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
    
    def scrape_google_search(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape business information from Google search results"""
        
        leads = []
        results_per_query = max(5, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # Build search query
                    query = f"{keyword} business {location} contact email"
                    search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={results_per_query}"
                    
                    logger.info(f"Scraping Google for: {keyword} in {location}")
                    
                    soup = self._make_request(search_url)
                    if not soup:
                        continue
                    
                    # Parse search results
                    for result in soup.find_all('div', class_='g')[:results_per_query]:
                        try:
                            # Extract title (company name)
                            title_elem = result.find('h3')
                            if not title_elem:
                                continue
                            
                            company_name = title_elem.get_text().strip()
                            
                            # Skip if not a business name
                            if any(skip in company_name.lower() for skip in ['linkedin', 'facebook', 'yelp', 'wikipedia']):
                                continue
                            
                            # Extract URL
                            link_elem = result.find('a', href=True)
                            website = link_elem['href'] if link_elem else None
                            
                            # Extract snippet text
                            snippet_elem = result.find('span', class_='aCOpRe')
                            snippet = snippet_elem.get_text() if snippet_elem else ''
                            
                            # Extract contact info from snippet
                            email = self._extract_email(snippet)
                            phone = self._extract_phone(snippet)
                            
                            lead_data = {
                                'company_name': company_name,
                                'website': website,
                                'email': email,
                                'phone': phone,
                                'industry': keyword,
                                'location': location,
                                'source': 'google-search',
                                'source_url': search_url
                            }
                            
                            leads.append(lead_data)
                            logger.debug(f"Found lead: {company_name}")
                            
                        except Exception as e:
                            logger.warning(f"Error parsing search result: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error scraping Google for {keyword} in {location}: {str(e)}")
                    continue
        
        logger.info(f"Google search completed. Found {len(leads)} leads.")
        return leads[:max_results]
    
    def scrape_yellow_pages(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 50
    ) -> List[Dict]:
        """Scrape business listings from Yellow Pages Australia"""
        
        leads = []
        results_per_query = max(5, max_results // (len(keywords) * len(locations)))
        
        for keyword in keywords:
            for location in locations:
                if len(leads) >= max_results:
                    break
                
                try:
                    # Build Yellow Pages URL
                    location_slug = location.replace(', ', '-').replace(' ', '-').lower()
                    keyword_slug = keyword.replace(' ', '-').lower()
                    url = f"https://www.yellowpages.com.au/search/listings?clue={quote_plus(keyword)}&locationClue={quote_plus(location)}"
                    
                    logger.info(f"Scraping Yellow Pages for: {keyword} in {location}")
                    
                    soup = self._make_request(url)
                    if not soup:
                        continue
                    
                    # Parse listings
                    listings = soup.find_all('div', class_='listing')[:results_per_query]
                    
                    for listing in listings:
                        try:
                            # Extract business name
                            name_elem = listing.find('a', class_='listing-name')
                            if not name_elem:
                                continue
                            
                            company_name = name_elem.get_text().strip()
                            
                            # Extract contact info
                            phone_elem = listing.find('a', class_='click-to-call')
                            phone = phone_elem.get_text().strip() if phone_elem else None
                            
                            # Extract address
                            address_elem = listing.find('p', class_='listing-address')
                            address = address_elem.get_text().strip() if address_elem else None
                            
                            # Extract website
                            website_elem = listing.find('a', class_='contact-url')
                            website = website_elem['href'] if website_elem else None
                            
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
                            logger.warning(f"Error parsing Yellow Pages listing: {str(e)}")
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
        """Scrape from multiple business directories"""
        
        leads = []
        
        # Hotfrog Australia
        try:
            hotfrog_leads = self._scrape_hotfrog(keywords, locations, max_results // 2)
            leads.extend(hotfrog_leads)
        except Exception as e:
            logger.error(f"Error scraping Hotfrog: {str(e)}")
        
        # True Local
        try:
            truelocal_leads = self._scrape_truelocal(keywords, locations, max_results // 2)
            leads.extend(truelocal_leads)
        except Exception as e:
            logger.error(f"Error scraping TrueLocal: {str(e)}")
        
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
                    
                    soup = self._make_request(url)
                    if not soup:
                        continue
                    
                    for listing in soup.find_all('div', class_='listing-item')[:results_per_query]:
                        try:
                            name_elem = listing.find('a', class_='listing-title')
                            if not name_elem:
                                continue
                            
                            lead_data = {
                                'company_name': name_elem.get_text().strip(),
                                'industry': keyword,
                                'location': location,
                                'source': 'business-directory',
                                'source_url': url
                            }
                            
                            # Try to extract more info
                            phone_elem = listing.find('span', class_='phone')
                            if phone_elem:
                                lead_data['phone'] = phone_elem.get_text().strip()
                            
                            leads.append(lead_data)
                            
                        except Exception as e:
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
                    location_slug = location.replace(', ', '/').replace(' ', '-').lower()
                    url = f"https://www.truelocal.com.au/search/{quote_plus(keyword)}/{location_slug}"
                    
                    soup = self._make_request(url)
                    if not soup:
                        continue
                    
                    for listing in soup.find_all('div', class_='search-result')[:results_per_query]:
                        try:
                            name_elem = listing.find('h3', class_='name')
                            if not name_elem:
                                continue
                            
                            lead_data = {
                                'company_name': name_elem.get_text().strip(),
                                'industry': keyword,
                                'location': location,
                                'source': 'business-directory',
                                'source_url': url
                            }
                            
                            leads.append(lead_data)
                            
                        except Exception as e:
                            continue
                    
                except Exception as e:
                    logger.warning(f"Error scraping TrueLocal: {str(e)}")
        
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

