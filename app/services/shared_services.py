"""
Shared Service Instances
Singleton instances shared across all blueprints
"""

from app.services.lead_manager import LeadManager
from app.services.ai_analyzer import AILeadAnalyzer

# Shared instances - these are singletons used across all blueprints
lead_manager = LeadManager()
ai_analyzer = AILeadAnalyzer()
