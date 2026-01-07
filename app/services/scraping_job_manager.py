"""
Scraping Job Manager
Handles scraping job scheduling, progress tracking, and result management
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import json
from pathlib import Path
import threading
from loguru import logger
import uuid

from app.config import Config


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = 'pending'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class ScrapingJob:
    """Scraping job data class"""
    
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    
    # Job Parameters
    keywords: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=lambda: ['google_search', 'yellow_pages'])
    max_leads: int = 100
    
    # AI Processing
    use_ai_analysis: bool = True
    ai_model: str = 'gpt-4'
    
    # Progress Tracking
    total_leads_found: int = 0
    leads_processed: int = 0
    leads_validated: int = 0
    errors: List[str] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: int = 0  # seconds
    
    # Results
    leads_data: List[Dict] = field(default_factory=list)
    export_path: Optional[str] = None
    
    # Metadata
    user_id: Optional[str] = None
    notes: str = ''
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'keywords': self.keywords,
            'locations': self.locations,
            'sources': self.sources,
            'max_leads': self.max_leads,
            'use_ai_analysis': self.use_ai_analysis,
            'ai_model': self.ai_model,
            'total_leads_found': self.total_leads_found,
            'leads_processed': self.leads_processed,
            'leads_validated': self.leads_validated,
            'errors': self.errors,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_duration': self.estimated_duration,
            'export_path': self.export_path,
            'user_id': self.user_id,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScrapingJob':
        """Create from dictionary"""
        job = cls(
            job_id=data.get('job_id', str(uuid.uuid4())),
            status=JobStatus(data.get('status', 'pending')),
            keywords=data.get('keywords', []),
            locations=data.get('locations', []),
            sources=data.get('sources', ['google_search', 'yellow_pages']),
            max_leads=data.get('max_leads', 100),
            use_ai_analysis=data.get('use_ai_analysis', True),
            ai_model=data.get('ai_model', 'gpt-4'),
            total_leads_found=data.get('total_leads_found', 0),
            leads_processed=data.get('leads_processed', 0),
            leads_validated=data.get('leads_validated', 0),
            errors=data.get('errors', []),
            export_path=data.get('export_path'),
            user_id=data.get('user_id'),
            notes=data.get('notes', '')
        )
        
        # Handle datetime conversion
        if isinstance(data.get('created_at'), str):
            job.created_at = datetime.fromisoformat(data['created_at'])
        
        if isinstance(data.get('started_at'), str):
            job.started_at = datetime.fromisoformat(data['started_at'])
        
        if isinstance(data.get('completed_at'), str):
            job.completed_at = datetime.fromisoformat(data['completed_at'])
        
        job.estimated_duration = data.get('estimated_duration', 0)
        
        return job
    
    def get_progress_percentage(self) -> float:
        """Get job progress as percentage"""
        if self.max_leads == 0:
            return 0.0
        return min(100.0, (self.leads_processed / self.max_leads) * 100)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        start = self.started_at or self.created_at
        end = self.completed_at or datetime.utcnow()
        return (end - start).total_seconds()


class ScrapingJobManager:
    """Manager for scraping jobs"""
    
    def __init__(self):
        """Initialize job manager"""
        self.config = Config()
        self.jobs: Dict[str, ScrapingJob] = {}
        self.jobs_lock = threading.Lock()
        self.job_storage_dir = Path(self.config.EXPORT_FOLDER) / 'scraping_jobs'
        self.job_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing jobs
        self._load_jobs_from_disk()
        
        logger.info("ScrapingJobManager initialized")
    
    def create_job(
        self,
        keywords: List[str],
        locations: List[str],
        sources: List[str] = None,
        max_leads: int = 100,
        use_ai_analysis: bool = True,
        user_id: Optional[str] = None,
        notes: str = ''
    ) -> ScrapingJob:
        """Create a new scraping job"""
        if sources is None:
            sources = ['google_search', 'yellow_pages']
        
        job = ScrapingJob(
            keywords=keywords,
            locations=locations,
            sources=sources,
            max_leads=max_leads,
            use_ai_analysis=use_ai_analysis,
            user_id=user_id,
            notes=notes
        )
        
        with self.jobs_lock:
            self.jobs[job.job_id] = job
        
        self._save_job_to_disk(job)
        logger.info(f"Created job: {job.job_id}")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ScrapingJob]:
        """List jobs with optional filtering"""
        jobs = list(self.jobs.values())
        
        # Filter by status
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Filter by user
        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        
        # Sort by creation date (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """Update job status"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        with self.jobs_lock:
            job.status = status
            
            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
            
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.utcnow()
        
        self._save_job_to_disk(job)
        logger.info(f"Job {job_id} status updated to {status.value}")
        
        return True
    
    def update_job_progress(
        self,
        job_id: str,
        leads_found: int = None,
        leads_processed: int = None,
        leads_validated: int = None,
        error: str = None
    ) -> bool:
        """Update job progress"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        with self.jobs_lock:
            if leads_found is not None:
                job.total_leads_found = leads_found
            
            if leads_processed is not None:
                job.leads_processed = leads_processed
            
            if leads_validated is not None:
                job.leads_validated = leads_validated
            
            if error:
                job.errors.append(f"[{datetime.utcnow().isoformat()}] {error}")
        
        self._save_job_to_disk(job)
        
        return True
    
    def add_leads_to_job(self, job_id: str, leads: List[Dict]) -> bool:
        """Add leads to job"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        with self.jobs_lock:
            job.leads_data.extend(leads)
        
        self._save_job_to_disk(job)
        
        return True
    
    def set_job_export_path(self, job_id: str, export_path: str) -> bool:
        """Set export path for job"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        with self.jobs_lock:
            job.export_path = export_path
        
        self._save_job_to_disk(job)
        
        return True
    
    def _save_job_to_disk(self, job: ScrapingJob) -> None:
        """Save job to disk"""
        try:
            job_file = self.job_storage_dir / f"{job.job_id}.json"
            
            # Don't save full leads data to avoid large files
            job_data = job.to_dict()
            job_data['leads_data'] = []  # Clear to reduce file size
            
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving job to disk: {str(e)}")
    
    def _load_jobs_from_disk(self) -> None:
        """Load jobs from disk"""
        try:
            if not self.job_storage_dir.exists():
                return
            
            for job_file in self.job_storage_dir.glob('*.json'):
                try:
                    with open(job_file, 'r') as f:
                        data = json.load(f)
                        job = ScrapingJob.from_dict(data)
                        self.jobs[job.job_id] = job
                
                except Exception as e:
                    logger.warning(f"Error loading job from {job_file}: {str(e)}")
            
            logger.info(f"Loaded {len(self.jobs)} jobs from disk")
        
        except Exception as e:
            logger.error(f"Error loading jobs from disk: {str(e)}")
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Clean up old completed jobs
        
        Args:
            days: Delete jobs older than this many days
        
        Returns:
            Number of jobs deleted
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        jobs_to_delete = []
        
        for job_id, job in self.jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if job.completed_at and job.completed_at < cutoff_date:
                    jobs_to_delete.append(job_id)
        
        with self.jobs_lock:
            for job_id in jobs_to_delete:
                del self.jobs[job_id]
                
                # Delete job file
                job_file = self.job_storage_dir / f"{job_id}.json"
                if job_file.exists():
                    job_file.unlink()
        
        logger.info(f"Cleaned up {len(jobs_to_delete)} old jobs")
        
        return len(jobs_to_delete)
    
    def get_job_statistics(self) -> Dict:
        """Get statistics about all jobs"""
        stats = {
            'total_jobs': len(self.jobs),
            'by_status': {},
            'total_leads_found': 0,
            'total_leads_processed': 0,
            'average_processing_time': 0
        }
        
        processing_times = []
        
        for job in self.jobs.values():
            # Count by status
            status_key = job.status.value
            stats['by_status'][status_key] = stats['by_status'].get(status_key, 0) + 1
            
            # Sum leads
            stats['total_leads_found'] += job.total_leads_found
            stats['total_leads_processed'] += job.leads_processed
            
            # Track processing times
            if job.completed_at and job.started_at:
                elapsed = (job.completed_at - job.started_at).total_seconds()
                processing_times.append(elapsed)
        
        if processing_times:
            stats['average_processing_time'] = sum(processing_times) / len(processing_times)
        
        return stats
