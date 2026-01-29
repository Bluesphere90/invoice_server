"""
Collector Job Manager

Manages background collector jobs with in-memory tracking.
"""
import uuid
import threading
from datetime import date, datetime
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from backend.observability.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollectorJob:
    """Represents a collector job."""
    job_id: str
    tax_code: str
    from_date: date
    to_date: date
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    message: str = ""
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    invoices_found: int = 0
    invoices_processed: int = 0


class JobManager:
    """
    Singleton job manager for collector jobs.
    Uses in-memory storage with thread safety.
    """
    _instance: Optional['JobManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._jobs: Dict[str, CollectorJob] = {}
                    cls._instance._jobs_lock = threading.Lock()
        return cls._instance
    
    def create_job(self, tax_code: str, from_date: date, to_date: date) -> CollectorJob:
        """Create a new collector job."""
        job_id = str(uuid.uuid4())[:8]  # Short UUID
        job = CollectorJob(
            job_id=job_id,
            tax_code=tax_code,
            from_date=from_date,
            to_date=to_date,
        )
        
        with self._jobs_lock:
            self._jobs[job_id] = job
        
        logger.info(f"Created job {job_id} for {tax_code}: {from_date} to {to_date}")
        return job
    
    def get_job(self, job_id: str) -> Optional[CollectorJob]:
        """Get job by ID."""
        with self._jobs_lock:
            return self._jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        invoices_found: Optional[int] = None,
        invoices_processed: Optional[int] = None,
    ):
        """Update job status."""
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            if status is not None:
                job.status = status
                if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    job.completed_at = datetime.now()
            
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            if invoices_found is not None:
                job.invoices_found = invoices_found
            if invoices_processed is not None:
                job.invoices_processed = invoices_processed
    
    def is_running_for(self, tax_code: str) -> bool:
        """Check if a job is already running for a tax code."""
        with self._jobs_lock:
            for job in self._jobs.values():
                if job.tax_code == tax_code and job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                    return True
        return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove completed jobs older than max_age_hours."""
        cutoff = datetime.now()
        with self._jobs_lock:
            to_remove = [
                job_id for job_id, job in self._jobs.items()
                if job.completed_at and 
                   (cutoff - job.completed_at).total_seconds() > max_age_hours * 3600
            ]
            for job_id in to_remove:
                del self._jobs[job_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")


def run_collector_job(job_id: str, company: dict, from_date: date, to_date: date):
    """
    Execute collector for a specific company in background.
    This is run in a separate thread.
    """
    from backend.database import get_connection, init_database
    from backend.database.repository import InvoiceRepository

    from backend.database.company_repository import CompanyRepository
    from backend.database.item_repository import InvoiceItemRepository
    from backend.collector.http import HoaDonHttpClient, LoginService, ProfileService
    from backend.collector.captcha import SvgCaptchaSolver
    from backend.collector.invoice import InvoiceListService, InvoiceDetailWorker
    
    manager = JobManager()
    
    try:
        manager.update_job(job_id, status=JobStatus.RUNNING, message="Đang khởi tạo...")
        
        tax_code = company['tax_code']
        username = company['username']
        password = company['password']
        
        logger.info(f"Job {job_id}: Starting collector for {tax_code}")
        
        # Initialize database connection for this thread
        init_database()
        conn = get_connection()
        invoice_repo = InvoiceRepository(conn)

        company_repo = CompanyRepository(conn)
        item_repo = InvoiceItemRepository(conn)
        
        # Create HTTP client and login
        manager.update_job(job_id, message="Đang đăng nhập...")
        http_client = HoaDonHttpClient()
        captcha_solver = SvgCaptchaSolver()
        login_service = LoginService(http_client, captcha_solver)
        
        token = login_service.login(username, password)
        logger.info(f"Job {job_id}: Login successful")
        
        # Get profile
        manager.update_job(job_id, message="Đang lấy thông tin profile...")
        
        # Add a small delay for GDT system stability
        import time
        time.sleep(2)
        
        profile_service = ProfileService(http_client)
        profile = profile_service.fetch_profile()

        tax_code = profile["tax_code"]
        
        # Update company name from profile
        if profile.get("company_name"):
            logger.info(f"Job {job_id}: Updating company name to {profile['company_name']}")
            company_repo.update_company(tax_code, company_name=profile["company_name"])
        
        # Fetch invoice list
        manager.update_job(job_id, progress=10, message="Đang lấy danh sách hóa đơn...")
        list_service = InvoiceListService(http_client, invoice_repo)
        
        # Purchase invoices
        purchase_ids = list_service.fetch_invoice_identifiers(
            tax_code=tax_code,
            from_date=from_date,
            to_date=to_date,
            is_purchase=True
        )
        
        # Sold invoices
        sold_ids = list_service.fetch_invoice_identifiers(
            tax_code=tax_code,
            from_date=from_date,
            to_date=to_date,
            is_purchase=False
        )
        
        all_identifiers = purchase_ids + sold_ids
        total = len(all_identifiers)
        
        manager.update_job(
            job_id,
            progress=20,
            message=f"Tìm thấy {total} hóa đơn",
            invoices_found=total
        )
        
        logger.info(f"Job {job_id}: Found {len(purchase_ids)} purchase + {len(sold_ids)} sold = {total} invoices")
        
        # Download details
        detail_worker = InvoiceDetailWorker(http_client, invoice_repo, item_repo)
        processed = 0
        
        for i, identifier in enumerate(all_identifiers, 1):
            try:
                detail_worker.process(identifier)
                processed += 1
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to process {identifier.id}: {e}")
            
            progress = 20 + int((i / total) * 75) if total > 0 else 95
            manager.update_job(
                job_id,
                progress=progress,
                message=f"Đang xử lý {i}/{total}...",
                invoices_processed=processed
            )
        
        manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message=f"Hoàn thành! Đã xử lý {processed}/{total} hóa đơn",
            invoices_processed=processed
        )
        
        logger.info(f"Job {job_id}: Completed. Processed {processed}/{total} invoices")
        
    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error: {e}")
        manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
            message=f"Lỗi: {str(e)}"
        )
