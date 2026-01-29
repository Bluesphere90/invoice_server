"""Company API routes."""
from fastapi import APIRouter, HTTPException, Depends

from backend.database import get_db
from backend.database.company_repository import CompanyRepository
from backend.api.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
async def list_companies(conn = Depends(get_db)):
    """
    List all companies.
    """
    repo = CompanyRepository(conn)
    companies = repo.get_all_companies()
    
    items = [CompanyResponse(
        tax_code=c['tax_code'],
        company_name=c.get('company_name'),
        username=c['username'],
        is_active=c.get('is_active', True),
        last_sync=c.get('last_sync'),
        last_error=c.get('last_error'),
    ) for c in companies]
    
    return CompanyListResponse(items=items, total=len(items))


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    company: CompanyCreate,
    conn = Depends(get_db),
):
    """
    Add a new company.
    """
    repo = CompanyRepository(conn)
    
    # Check if exists
    existing = repo.get_company_by_tax_code(company.tax_code)
    if existing:
        raise HTTPException(status_code=400, detail="Company with this tax code already exists")
    
    repo.add_company(
        tax_code=company.tax_code,
        username=company.username,
        password=company.password,
        company_name=company.company_name,
    )
    
    return CompanyResponse(
        tax_code=company.tax_code,
        company_name=company.company_name,
        username=company.username,
        is_active=True,
    )


@router.get("/{tax_code}", response_model=CompanyResponse)
async def get_company(tax_code: str, conn = Depends(get_db)):
    """
    Get company by tax code.
    """
    repo = CompanyRepository(conn)
    company = repo.get_company_by_tax_code(tax_code)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyResponse(
        tax_code=company['tax_code'],
        company_name=company.get('company_name'),
        username=company['username'],
        is_active=company.get('is_active', True),
        last_sync=company.get('last_sync'),
        last_error=company.get('last_error'),
    )


@router.put("/{tax_code}", response_model=CompanyResponse)
async def update_company(
    tax_code: str,
    data: CompanyUpdate,
    conn = Depends(get_db),
):
    """
    Update company details.
    """
    repo = CompanyRepository(conn)
    company = repo.get_company_by_tax_code(tax_code)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        repo.update_company(tax_code, **update_data)
    
    # Fetch updated
    updated = repo.get_company_by_tax_code(tax_code)
    return CompanyResponse(
        tax_code=updated['tax_code'],
        company_name=updated.get('company_name'),
        username=updated['username'],
        is_active=updated.get('is_active', True),
        last_sync=updated.get('last_sync'),
        last_error=updated.get('last_error'),
    )


@router.delete("/{tax_code}", status_code=204)
async def delete_company(tax_code: str, conn = Depends(get_db)):
    """
    Deactivate company (soft delete).
    """
    repo = CompanyRepository(conn)
    company = repo.get_company_by_tax_code(tax_code)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    repo.deactivate_company(tax_code)
    return None
