"""Collector API Schemas."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class CollectorRunRequest(BaseModel):
    """Request to run collector for a company."""
    tax_code: str
    from_date: date
    to_date: date


class CollectorRunResponse(BaseModel):
    """Response after starting a collector job."""
    job_id: str
    status: str
    message: str


class CollectorStatusResponse(BaseModel):
    """Response for collector job status."""
    job_id: str
    tax_code: str
    status: str
    progress: int
    message: str
    error: Optional[str] = None
    invoices_found: int = 0
    invoices_processed: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
