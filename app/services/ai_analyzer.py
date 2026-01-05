"""
AI Lead Analyzer Service
Uses OpenAI/Azure OpenAI for intelligent lead analysis and scoring
"""

import os
from typing import Dict, Optional, List
from loguru import logger
import json

try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. AI analysis will use fallback scoring.")

from app.config import Config
from app.models.lead import Lead


class AILeadAnalyzer:
    """Service for AI-powered lead analysis"""
    
    def __init__(self):
        """Initialize AI analyzer"""
        self.config = Config()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available. Using fallback analysis.")
            return
        
        try:
            if self.config.USE_AZURE_OPENAI and self.config.AZURE_OPENAI_API_KEY:
                self.client = AzureOpenAI(
                    api_key=self.config.AZURE_OPENAI_API_KEY,
                    api_version="2024-02-15-preview",
                    azure_endpoint=self.config.AZURE_OPENAI_ENDPOINT
                )
                logger.info("Initialized Azure OpenAI client")
            elif self.config.OPENAI_API_KEY:
                self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)
                logger.info("Initialized OpenAI client")
            else:
                logger.warning("No OpenAI API key configured. Using fallback analysis.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    def analyze_lead(self, lead: Lead) -> Dict:
        """Perform comprehensive AI analysis on a lead"""
        
        if self.client:
            try:
                return self._ai_analyze(lead)
            except Exception as e:
                logger.error(f"AI analysis failed: {str(e)}. Using fallback.")
        
        return self._fallback_analyze(lead)
    
    def _ai_analyze(self, lead: Lead) -> Dict:
        """Perform AI-powered analysis using OpenAI"""
        
        # Build context about the lead
        lead_info = f"""
        Company Name: {lead.company_name}
        Industry: {lead.industry or 'Unknown'}
        Location: {lead.location or 'Unknown'}
        Website: {lead.website or 'Not provided'}
        Contact: {lead.contact_name or 'Unknown'}
        Email: {lead.email or 'Not provided'}
        Phone: {lead.phone or 'Not provided'}
        """
        
        prompt = f"""You are a lead scoring and analysis expert for Scent Australia, a company specializing in premium fragrance solutions for businesses.

Analyze the following lead and provide a comprehensive assessment:

{lead_info}

Target Industries for Scent Australia:
- Luxury retail stores
- Hotels and hospitality
- Spas and wellness centers
- Corporate offices
- Boutique fashion stores
- Restaurants and cafes
- Healthcare facilities
- Real estate (showrooms, open homes)

Please provide your analysis in the following JSON format:
{{
    "score": <0-100 integer>,
    "priority": "<high/medium/low>",
    "fit_assessment": "<excellent/good/moderate/poor>",
    "reasoning": "<brief explanation of the score>",
    "industry_relevance": <0-100 integer>,
    "potential_value": "<high/medium/low>",
    "recommended_products": ["<product1>", "<product2>"],
    "talking_points": ["<point1>", "<point2>", "<point3>"],
    "next_steps": ["<action1>", "<action2>"],
    "risk_factors": ["<risk1>", "<risk2>"],
    "confidence_level": <0-100 integer>
}}

Focus on:
1. How well the company fits Scent Australia's target market
2. Potential for fragrance/scent marketing solutions
3. Estimated business value
4. Any red flags or concerns
"""
        
        try:
            if self.config.USE_AZURE_OPENAI:
                response = self.client.chat.completions.create(
                    model=self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": "You are a B2B sales lead analyst specializing in fragrance industry opportunities."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a B2B sales lead analyst specializing in fragrance industry opportunities."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON. Using partial extraction.")
                analysis = self._extract_partial_analysis(content)
            
            logger.info(f"AI analysis completed for {lead.company_name}. Score: {analysis.get('score', 'N/A')}")
            return analysis
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _extract_partial_analysis(self, content: str) -> Dict:
        """Extract analysis from non-JSON response"""
        import re
        
        analysis = {
            'score': 50,
            'priority': 'medium',
            'fit_assessment': 'moderate',
            'reasoning': content[:500] if content else 'Analysis could not be parsed.',
            'industry_relevance': 50,
            'potential_value': 'medium',
            'recommended_products': [],
            'talking_points': [],
            'next_steps': ['Review lead manually'],
            'risk_factors': ['AI analysis incomplete'],
            'confidence_level': 30
        }
        
        # Try to extract score
        score_match = re.search(r'"score"\s*:\s*(\d+)', content)
        if score_match:
            analysis['score'] = int(score_match.group(1))
        
        return analysis
    
    def _fallback_analyze(self, lead: Lead) -> Dict:
        """Fallback analysis when AI is not available"""
        
        score = 50
        factors = []
        
        # Score based on available data
        if lead.email:
            score += 10
            factors.append("Has email contact (+10)")
        
        if lead.phone:
            score += 10
            factors.append("Has phone contact (+10)")
        
        if lead.website:
            score += 5
            factors.append("Has website (+5)")
        
        if lead.contact_name:
            score += 5
            factors.append("Has contact name (+5)")
        
        # Industry relevance
        high_value_industries = ['hospitality', 'hotel', 'spa', 'wellness', 'luxury', 'retail', 'boutique']
        if lead.industry:
            industry_lower = lead.industry.lower()
            for hvi in high_value_industries:
                if hvi in industry_lower:
                    score += 15
                    factors.append(f"High-value industry: {lead.industry} (+15)")
                    break
        
        # Location bonus (major Australian cities)
        major_cities = ['sydney', 'melbourne', 'brisbane', 'perth']
        if lead.location:
            location_lower = lead.location.lower()
            for city in major_cities:
                if city in location_lower:
                    score += 5
                    factors.append(f"Major city location (+5)")
                    break
        
        # Cap score
        score = min(100, max(0, score))
        
        # Determine priority
        if score >= 80:
            priority = 'high'
            fit = 'excellent'
        elif score >= 60:
            priority = 'medium'
            fit = 'good'
        elif score >= 40:
            priority = 'medium'
            fit = 'moderate'
        else:
            priority = 'low'
            fit = 'poor'
        
        return {
            'score': score,
            'priority': priority,
            'fit_assessment': fit,
            'reasoning': f"Automated scoring based on available data. Factors: {', '.join(factors) if factors else 'Basic profile only'}",
            'industry_relevance': score,
            'potential_value': priority,
            'recommended_products': self._get_recommended_products(lead),
            'talking_points': self._get_talking_points(lead),
            'next_steps': ['Verify contact information', 'Research company online', 'Prepare initial outreach'],
            'risk_factors': ['Analysis based on limited data'],
            'confidence_level': 50,
            'analysis_type': 'fallback'
        }
    
    def _get_recommended_products(self, lead: Lead) -> List[str]:
        """Get recommended products based on industry"""
        
        industry = (lead.industry or '').lower()
        
        if any(x in industry for x in ['hotel', 'hospitality']):
            return ['Room Diffusers', 'Lobby Scent Systems', 'Amenity Lines']
        elif any(x in industry for x in ['spa', 'wellness']):
            return ['Aromatherapy Oils', 'Treatment Room Diffusers', 'Relaxation Blends']
        elif any(x in industry for x in ['retail', 'boutique']):
            return ['Store Ambient Scenting', 'Brand Signature Scents', 'Display Diffusers']
        elif any(x in industry for x in ['office', 'corporate']):
            return ['Office Scenting Systems', 'Meeting Room Fresheners', 'Productivity Blends']
        else:
            return ['Custom Scent Solutions', 'Ambient Diffusers', 'Air Care Systems']
    
    def _get_talking_points(self, lead: Lead) -> List[str]:
        """Generate talking points for sales outreach"""
        
        industry = (lead.industry or '').lower()
        points = [
            "Scent marketing can increase customer dwell time by up to 40%",
            "Custom fragrance solutions tailored to your brand identity"
        ]
        
        if any(x in industry for x in ['hotel', 'hospitality']):
            points.append("Hotels using signature scents report 20% higher guest satisfaction")
        elif any(x in industry for x in ['retail']):
            points.append("Retail scenting can boost sales by up to 11%")
        elif any(x in industry for x in ['spa', 'wellness']):
            points.append("Our therapeutic blends enhance relaxation and treatment outcomes")
        
        return points
    
    def quick_analyze(self, lead_data: Dict) -> Dict:
        """Quick analysis for preview purposes"""
        
        # Create temporary lead object
        lead = Lead.from_dict(lead_data)
        
        # Use fallback for quick analysis (faster)
        analysis = self._fallback_analyze(lead)
        analysis['preview'] = True
        
        return analysis
    
    def batch_analyze(self, leads: List[Lead]) -> List[Dict]:
        """Analyze multiple leads"""
        
        results = []
        for lead in leads:
            try:
                analysis = self.analyze_lead(lead)
                results.append({
                    'lead_id': lead.id,
                    'analysis': analysis,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'lead_id': lead.id,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def generate_outreach_email(self, lead: Lead) -> str:
        """Generate personalized outreach email"""
        
        if not self.client:
            return self._fallback_email(lead)
        
        try:
            prompt = f"""Generate a professional B2B sales outreach email for Scent Australia.

Lead Details:
- Company: {lead.company_name}
- Contact: {lead.contact_name or 'Business Owner'}
- Industry: {lead.industry or 'Business'}
- Location: {lead.location or 'Australia'}

Scent Australia offers:
- Custom fragrance solutions
- Ambient scenting systems
- Brand signature scents
- Scent marketing consultation

Write a personalized, professional email that:
1. Opens with relevance to their industry
2. Highlights benefits specific to their business type
3. Includes a clear call to action
4. Maintains a warm but professional tone

Keep it under 200 words."""

            response = self.client.chat.completions.create(
                model=self.config.OPENAI_MODEL if not self.config.USE_AZURE_OPENAI else self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are a professional B2B sales copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate email: {str(e)}")
            return self._fallback_email(lead)
    
    def _fallback_email(self, lead: Lead) -> str:
        """Generate a basic template email"""
        
        contact_name = lead.contact_name or "Business Owner"
        company_name = lead.company_name
        
        return f"""Subject: Elevate {company_name}'s Customer Experience with Scent Marketing

Dear {contact_name},

I hope this message finds you well. I'm reaching out from Scent Australia, Australia's leading provider of premium fragrance solutions for businesses.

We specialize in helping businesses like {company_name} create memorable customer experiences through the power of scent. Studies show that strategic scent marketing can significantly enhance brand perception and customer engagement.

I'd love to discuss how a customized scent solution could benefit your business. Would you be open to a brief call this week?

Best regards,
Scent Australia Team

---
Scent Australia | Premium Fragrance Solutions
www.scentaustralia.com.au"""

