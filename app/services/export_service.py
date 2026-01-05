"""
Data Export Service
Handles exporting leads to Excel and CSV formats
"""

import os
from typing import List
from datetime import datetime
from loguru import logger
import pandas as pd

from app.models.lead import Lead
from app.config import Config


class ExportService:
    """Service for exporting lead data"""
    
    def __init__(self):
        """Initialize export service"""
        self.config = Config()
        self.export_folder = self.config.EXPORT_FOLDER
        os.makedirs(self.export_folder, exist_ok=True)
    
    def _leads_to_dataframe(self, leads: List[Lead]) -> pd.DataFrame:
        """Convert leads to pandas DataFrame"""
        
        data = []
        for lead in leads:
            # Flatten AI analysis for export
            ai_analysis = lead.ai_analysis or {}
            
            row = {
                'ID': lead.id,
                'Company Name': lead.company_name,
                'Contact Name': lead.contact_name,
                'Email': lead.email,
                'Phone': lead.phone,
                'Website': lead.website,
                'Industry': lead.industry,
                'Location': lead.location,
                'Address': lead.address,
                'Company Size': lead.company_size,
                'Status': lead.status.value if hasattr(lead.status, 'value') else lead.status,
                'Priority': lead.priority.value if hasattr(lead.priority, 'value') else lead.priority,
                'Source': lead.source.value if hasattr(lead.source, 'value') else lead.source,
                'Score': lead.score,
                'Estimated Value': lead.estimated_value,
                'AI Fit Assessment': ai_analysis.get('fit_assessment', ''),
                'AI Reasoning': ai_analysis.get('reasoning', ''),
                'AI Confidence': ai_analysis.get('confidence_level', ''),
                'Recommended Products': ', '.join(ai_analysis.get('recommended_products', [])),
                'Talking Points': ' | '.join(ai_analysis.get('talking_points', [])),
                'Next Steps': ' | '.join(ai_analysis.get('next_steps', [])),
                'Tags': ', '.join(lead.tags) if lead.tags else '',
                'Notes': lead.notes,
                'Created At': lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '',
                'Updated At': lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else '',
                'Last Contacted': lead.last_contacted.strftime('%Y-%m-%d %H:%M:%S') if lead.last_contacted else '',
                'Source URL': lead.source_url
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def export_to_excel(self, leads: List[Lead], filename: str) -> str:
        """Export leads to Excel file"""
        
        filepath = os.path.join(self.export_folder, filename)
        
        try:
            df = self._leads_to_dataframe(leads)
            
            # Create Excel writer with formatting
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Leads', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Leads']
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#1a237e',  # Dark blue (Scent Australia brand)
                    'font_color': 'white',
                    'border': 1,
                    'text_wrap': True,
                    'valign': 'vcenter'
                })
                
                high_score_format = workbook.add_format({
                    'bg_color': '#c8e6c9',  # Light green
                    'border': 1
                })
                
                low_score_format = workbook.add_format({
                    'bg_color': '#ffcdd2',  # Light red
                    'border': 1
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Set column widths
                column_widths = {
                    'Company Name': 30,
                    'Contact Name': 20,
                    'Email': 30,
                    'Phone': 18,
                    'Website': 35,
                    'Industry': 20,
                    'Location': 20,
                    'Status': 12,
                    'Priority': 10,
                    'Score': 8,
                    'AI Reasoning': 50,
                    'Recommended Products': 40,
                    'Notes': 40
                }
                
                for col_num, col_name in enumerate(df.columns):
                    width = column_widths.get(col_name, 15)
                    worksheet.set_column(col_num, col_num, width)
                
                # Apply conditional formatting for scores
                score_col = list(df.columns).index('Score')
                worksheet.conditional_format(1, score_col, len(df), score_col, {
                    'type': 'cell',
                    'criteria': '>=',
                    'value': 80,
                    'format': high_score_format
                })
                worksheet.conditional_format(1, score_col, len(df), score_col, {
                    'type': 'cell',
                    'criteria': '<',
                    'value': 40,
                    'format': low_score_format
                })
                
                # Add summary sheet
                self._add_summary_sheet(writer, workbook, leads)
                
                # Freeze top row
                worksheet.freeze_panes(1, 0)
            
            logger.info(f"Exported {len(leads)} leads to Excel: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {str(e)}")
            raise
    
    def _add_summary_sheet(self, writer: pd.ExcelWriter, workbook, leads: List[Lead]):
        """Add a summary sheet to the Excel file"""
        
        # Calculate statistics
        total_leads = len(leads)
        avg_score = sum(l.score for l in leads) / total_leads if total_leads > 0 else 0
        total_value = sum(l.estimated_value for l in leads)
        
        # Count by status
        status_counts = {}
        for lead in leads:
            status = lead.status.value if hasattr(lead.status, 'value') else lead.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for lead in leads:
            priority = lead.priority.value if hasattr(lead.priority, 'value') else lead.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by industry
        industry_counts = {}
        for lead in leads:
            industry = lead.industry or 'Unknown'
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        # Create summary data
        summary_data = {
            'Metric': [
                'Export Date',
                'Total Leads',
                'Average Score',
                'Total Estimated Value',
                '',
                '--- By Status ---',
                *[f'  {k.title()}' for k in status_counts.keys()],
                '',
                '--- By Priority ---',
                *[f'  {k.title()}' for k in priority_counts.keys()],
                '',
                '--- Top Industries ---',
                *[f'  {k}' for k in list(industry_counts.keys())[:10]]
            ],
            'Value': [
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                total_leads,
                f'{avg_score:.1f}',
                f'${total_value:,.2f}',
                '',
                '',
                *[str(v) for v in status_counts.values()],
                '',
                '',
                *[str(v) for v in priority_counts.values()],
                '',
                '',
                *[str(v) for v in list(industry_counts.values())[:10]]
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1a237e',
            'font_color': 'white',
            'border': 1
        })
        
        for col_num, value in enumerate(summary_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 1, 25)
    
    def export_to_csv(self, leads: List[Lead], filename: str) -> str:
        """Export leads to CSV file"""
        
        filepath = os.path.join(self.export_folder, filename)
        
        try:
            df = self._leads_to_dataframe(leads)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            logger.info(f"Exported {len(leads)} leads to CSV: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            raise
    
    def export_to_json(self, leads: List[Lead], filename: str) -> str:
        """Export leads to JSON file"""
        
        filepath = os.path.join(self.export_folder, filename)
        
        try:
            import json
            
            data = {
                'exported_at': datetime.utcnow().isoformat(),
                'total_leads': len(leads),
                'leads': [lead.to_dict() for lead in leads]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(leads)} leads to JSON: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            raise

