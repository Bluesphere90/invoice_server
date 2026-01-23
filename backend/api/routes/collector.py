"""Collector API routes."""
import threading
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from backend.database import get_connection
from backend.database.company_repository import CompanyRepository
from backend.collector.job_manager import JobManager, JobStatus, run_collector_job
from backend.api.schemas.collector import (
    CollectorRunRequest,
    CollectorRunResponse,
    CollectorStatusResponse,
)

router = APIRouter(prefix="/collector", tags=["collector"])


def get_db():
    """Dependency to get database connection."""
    return get_connection()


@router.post("/run", response_model=CollectorRunResponse)
async def run_collector(
    request: CollectorRunRequest,
    conn=Depends(get_db),
):
    """
    Start collector job for a specific company and date range.
    The job runs in background and can be tracked via /status/{job_id}.
    """
    # Validate company exists and is active
    repo = CompanyRepository(conn)
    company = repo.get_company_by_tax_code(request.tax_code)
    
    if not company:
        raise HTTPException(status_code=404, detail="Không tìm thấy công ty")
    
    if not company.get('is_active', True):
        raise HTTPException(status_code=400, detail="Công ty đã bị vô hiệu hóa")
    
    # Check if already running
    manager = JobManager()
    if manager.is_running_for(request.tax_code):
        raise HTTPException(
            status_code=409,
            detail="Đang có job thu thập chạy cho công ty này"
        )
    
    # Validate date range
    if request.from_date > request.to_date:
        raise HTTPException(
            status_code=400,
            detail="Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc"
        )
    
    # Create job
    job = manager.create_job(
        tax_code=request.tax_code,
        from_date=request.from_date,
        to_date=request.to_date,
    )
    
    # Get full company info with password
    company_with_password = repo.get_company_with_password(request.tax_code)
    
    # Start collector in background thread
    thread = threading.Thread(
        target=run_collector_job,
        args=(job.job_id, company_with_password, request.from_date, request.to_date),
        daemon=True
    )
    thread.start()
    
    return CollectorRunResponse(
        job_id=job.job_id,
        status=job.status.value,
        message=f"Đã bắt đầu thu thập hóa đơn cho {request.tax_code}"
    )


@router.get("/status/{job_id}", response_model=CollectorStatusResponse)
async def get_collector_status(job_id: str):
    """
    Get status of a collector job.
    """
    manager = JobManager()
    job = manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    
    return CollectorStatusResponse(
        job_id=job.job_id,
        tax_code=job.tax_code,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        error=job.error,
        invoices_found=job.invoices_found,
        invoices_processed=job.invoices_processed,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
