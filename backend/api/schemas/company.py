"""Pydantic schemas for company data."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class CompanyBase(BaseModel):
    """Base company fields."""
    tax_code: str
    company_name: Optional[str] = None
    username: str
    is_active: bool = True


class CompanyCreate(CompanyBase):
    """Create company request."""
    password: str


class CompanyUpdate(BaseModel):
    """Update company request."""
    company_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Company response (no password)."""
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    
    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """List of companies."""
    items: list[CompanyResponse]
    total: int
