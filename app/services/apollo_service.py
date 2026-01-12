"""
Apollo.io Service
Lead generation using Apollo.io People and Organizations API
"""

import httpx
from typing import List, Dict, Optional, Any
from loguru import logger
from datetime import datetime
import asyncio
from app.config import Config


class ApolloService:
    """Service for fetching leads from Apollo.io API"""
    
    BASE_URL = "https://api.apollo.io/api/v1"
    
    def __init__(self):
        self.config = Config()
        self.api_key = self.config.APOLLO_API_KEY
        self.timeout = httpx.Timeout(30.0)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Apollo API requests"""
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.api_key
        }
    
    def _is_configured(self) -> bool:
        """Check if Apollo API is configured"""
        return bool(self.api_key)
    
    async def search_people(
        self,
        person_titles: Optional[List[str]] = None,
        person_locations: Optional[List[str]] = None,
        organization_locations: Optional[List[str]] = None,
        organization_industries: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        q_keywords: Optional[str] = None,
        per_page: int = 25,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for people using Apollo.io People API
        
        Args:
            person_titles: Job titles to filter (e.g., ["CEO", "Director"])
            person_locations: Person's location (e.g., ["Sydney, Australia"])
            organization_locations: Company HQ location
            organization_industries: Industries (e.g., ["retail", "hospitality"])
            organization_num_employees_ranges: Employee ranges (e.g., ["1,10", "11,50"])
            q_keywords: General keyword search
            per_page: Results per page (1-100)
            page: Page number
            
        Returns:
            Dict with people data and pagination info
        """
        if not self._is_configured():
            logger.error("Apollo API key not configured")
            return {"success": False, "error": "Apollo API key not configured", "people": []}
        
        endpoint = f"{self.BASE_URL}/mixed_people/search"
        
        payload = {
            "per_page": min(per_page, 100),
            "page": page
        }
        
        # Add optional filters
        if person_titles:
            payload["person_titles"] = person_titles
        if person_locations:
            payload["person_locations"] = person_locations
        if organization_locations:
            payload["organization_locations"] = organization_locations
        if organization_industries:
            payload["organization_industry_tag_ids"] = organization_industries
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges
        if q_keywords:
            payload["q_keywords"] = q_keywords
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Apollo People Search: Found {len(data.get('people', []))} results")
                    return {
                        "success": True,
                        "people": data.get("people", []),
                        "pagination": data.get("pagination", {}),
                        "total": data.get("pagination", {}).get("total_entries", 0)
                    }
                elif response.status_code == 401:
                    logger.error("Apollo API authentication failed")
                    return {"success": False, "error": "Invalid API key", "people": []}
                elif response.status_code == 422:
                    logger.error(f"Apollo API validation error: {response.text}")
                    return {"success": False, "error": "Invalid search parameters", "people": []}
                else:
                    logger.error(f"Apollo API error: {response.status_code} - {response.text}")
                    return {"success": False, "error": f"API error: {response.status_code}", "people": []}
                    
        except httpx.TimeoutException:
            logger.error("Apollo API request timed out")
            return {"success": False, "error": "Request timed out", "people": []}
        except Exception as e:
            logger.error(f"Apollo API error: {str(e)}")
            return {"success": False, "error": str(e), "people": []}
    
    async def search_organizations(
        self,
        organization_locations: Optional[List[str]] = None,
        organization_industries: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        q_organization_keyword: Optional[str] = None,
        per_page: int = 25,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for organizations/companies using Apollo.io Organizations API
        
        Args:
            organization_locations: Company HQ locations
            organization_industries: Industries to filter
            organization_num_employees_ranges: Employee count ranges
            q_organization_keyword: Organization keyword search
            per_page: Results per page (1-100)
            page: Page number
            
        Returns:
            Dict with organizations data and pagination info
        """
        if not self._is_configured():
            logger.error("Apollo API key not configured")
            return {"success": False, "error": "Apollo API key not configured", "organizations": []}
        
        endpoint = f"{self.BASE_URL}/mixed_companies/search"
        
        payload = {
            "per_page": min(per_page, 100),
            "page": page
        }
        
        if organization_locations:
            payload["organization_locations"] = organization_locations
        if organization_industries:
            payload["organization_industry_tag_ids"] = organization_industries
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges
        if q_organization_keyword:
            payload["q_organization_keyword"] = q_organization_keyword
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Apollo Org Search: Found {len(data.get('organizations', []))} results")
                    return {
                        "success": True,
                        "organizations": data.get("organizations", []),
                        "pagination": data.get("pagination", {}),
                        "total": data.get("pagination", {}).get("total_entries", 0)
                    }
                else:
                    logger.error(f"Apollo API error: {response.status_code}")
                    return {"success": False, "error": f"API error: {response.status_code}", "organizations": []}
                    
        except Exception as e:
            logger.error(f"Apollo API error: {str(e)}")
            return {"success": False, "error": str(e), "organizations": []}
    
    async def enrich_person(self, email: str = None, linkedin_url: str = None) -> Dict[str, Any]:
        """
        Enrich a person's data using Apollo.io People Enrichment API
        
        Args:
            email: Person's email address
            linkedin_url: Person's LinkedIn profile URL
            
        Returns:
            Enriched person data
        """
        if not self._is_configured():
            return {"success": False, "error": "Apollo API key not configured"}
        
        if not email and not linkedin_url:
            return {"success": False, "error": "Email or LinkedIn URL required"}
        
        endpoint = f"{self.BASE_URL}/people/match"
        
        payload = {}
        if email:
            payload["email"] = email
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "person": data.get("person", {})}
                else:
                    return {"success": False, "error": f"API error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Apollo enrichment error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def transform_person_to_lead(self, person: Dict) -> Dict:
        """
        Transform Apollo person data to our Lead format
        
        Args:
            person: Apollo person object
            
        Returns:
            Lead data dictionary
        """
        organization = person.get("organization", {}) or {}
        
        return {
            "company_name": organization.get("name", person.get("organization_name", "Unknown")),
            "contact_name": person.get("name", f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()),
            "email": person.get("email"),
            "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
            "website": organization.get("website_url") or organization.get("primary_domain"),
            "linkedin_url": person.get("linkedin_url"),
            "industry": organization.get("industry") or ", ".join(organization.get("keywords", [])[:3]),
            "location": person.get("city") or person.get("state") or person.get("country"),
            "company_size": organization.get("estimated_num_employees"),
            "annual_revenue": organization.get("annual_revenue_printed"),
            "title": person.get("title"),
            "seniority": person.get("seniority"),
            "departments": person.get("departments", []),
            "source": "apollo.io",
            "source_url": f"https://app.apollo.io/#/people/{person.get('id')}" if person.get('id') else None,
            "apollo_id": person.get("id"),
            "raw_data": person  # Store original data for AI analysis
        }
    
    def transform_organization_to_lead(self, org: Dict) -> Dict:
        """
        Transform Apollo organization data to our Lead format
        
        Args:
            org: Apollo organization object
            
        Returns:
            Lead data dictionary
        """
        return {
            "company_name": org.get("name", "Unknown"),
            "contact_name": None,
            "email": None,
            "phone": org.get("phone"),
            "website": org.get("website_url") or org.get("primary_domain"),
            "linkedin_url": org.get("linkedin_url"),
            "industry": org.get("industry") or ", ".join(org.get("keywords", [])[:3]),
            "location": f"{org.get('city', '')}, {org.get('state', '')}".strip(", "),
            "company_size": org.get("estimated_num_employees"),
            "annual_revenue": org.get("annual_revenue_printed"),
            "source": "apollo.io",
            "source_url": f"https://app.apollo.io/#/companies/{org.get('id')}" if org.get('id') else None,
            "apollo_id": org.get("id"),
            "raw_data": org
        }


# Synchronous wrapper for use in Flask routes
def search_people_sync(
    person_titles: Optional[List[str]] = None,
    person_locations: Optional[List[str]] = None,
    organization_locations: Optional[List[str]] = None,
    organization_industries: Optional[List[str]] = None,
    q_keywords: Optional[str] = None,
    per_page: int = 25,
    page: int = 1
) -> Dict[str, Any]:
    """Synchronous wrapper for search_people"""
    service = ApolloService()
    return asyncio.run(service.search_people(
        person_titles=person_titles,
        person_locations=person_locations,
        organization_locations=organization_locations,
        organization_industries=organization_industries,
        q_keywords=q_keywords,
        per_page=per_page,
        page=page
    ))


def search_organizations_sync(
    organization_locations: Optional[List[str]] = None,
    organization_industries: Optional[List[str]] = None,
    q_organization_keyword: Optional[str] = None,
    per_page: int = 25,
    page: int = 1
) -> Dict[str, Any]:
    """Synchronous wrapper for search_organizations"""
    service = ApolloService()
    return asyncio.run(service.search_organizations(
        organization_locations=organization_locations,
        organization_industries=organization_industries,
        q_organization_keyword=q_organization_keyword,
        per_page=per_page,
        page=page
    ))
