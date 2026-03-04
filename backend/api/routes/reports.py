"""Reports API routes."""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from backend.database import get_db
from backend.api.auth import get_current_user, UserAuth
from backend.database.user_repository import UserRepository

router = APIRouter(prefix="/reports", tags=["reports"])


class InvoiceFlowReportItem(BaseModel):
    """Individual invoice item for the flow report."""
    id: str
    date: str
    type: str  # 'in' for purchase, 'out' for sale
    company_name: str
    tax_code: str
    amount: float  # Positive for incoming, negative for outgoing
    tax_amount: float  # Positive for incoming, negative for outgoing
    invoice_number: str
    invoice_symbol: str


class InvoiceFlowReportResponse(BaseModel):
    """Response model for the invoice flow report."""
    items: List[InvoiceFlowReportItem]
    total_incoming_amount: float
    total_outgoing_amount: float
    total_incoming_tax: float
    total_outgoing_tax: float
    net_tax_obligation: float  # outgoing_tax - incoming_tax


class VATTaxTimelineItem(BaseModel):
    """Individual VAT tax timeline item."""
    date: str
    incoming_tax: float
    outgoing_tax: float
    net_tax: float  # outgoing_tax - incoming_tax


class VATTaxTimelineResponse(BaseModel):
    """Response model for the VAT tax timeline report."""
    items: List[VATTaxTimelineItem]
    total_incoming_tax: float
    total_outgoing_tax: float
    net_tax_obligation: float


def build_company_restriction_clause(user_id: int, role: str, conn, tax_code_field: str, buyer_tax_code_field: str):
    """Build company restriction clause for non-admin users."""
    if role == "admin":
        return "1=1", []
    
    user_repo = UserRepository(conn)
    user_companies = user_repo.get_user_companies(user_id)
    company_tax_codes = [comp['tax_code'] for comp in user_companies]
    
    if not company_tax_codes:
        return "1=0", []  # No access
    
    company_placeholders = ",".join(["%s"] * len(company_tax_codes))
    clause = f"({tax_code_field} IN ({company_placeholders}) OR {buyer_tax_code_field} IN ({company_placeholders}))"
    params = company_tax_codes + company_tax_codes
    
    return clause, params


@router.get("/invoice-flow", response_model=InvoiceFlowReportResponse)
async def get_invoice_flow_report(
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    tax_code: Optional[str] = Query(None, description="Filter by company tax code"),
    current_user: UserAuth = Depends(get_current_user),
    conn = Depends(get_db),
):
    """
    Get invoice flow report combining both incoming and outgoing invoices.
    Incoming invoices (purchases) have positive amounts, outgoing invoices (sales) have negative amounts.
    """
    # Build base query conditions
    conditions = []
    params = []

    if from_date:
        conditions.append("tdlap >= %s")
        params.append(from_date.isoformat())
    if to_date:
        conditions.append("tdlap <= %s")
        params.append(to_date.isoformat() + "T23:59:59")
    
    # For non-admin users, restrict access to assigned companies
    company_clause, company_params = build_company_restriction_clause(
        current_user.id, current_user.role, conn, "nbmst", "nmmst"
    )
    conditions.append(company_clause)
    params.extend(company_params)
    
    # If specific tax code is provided, add it to the condition
    if tax_code:
        conditions.append("(nbmst = %s OR nmmst = %s)")
        params.extend([tax_code, tax_code])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Query to get all invoices
    query = f"""
        SELECT
            id, tdlap, nbmst, nbten, nmmst, nmten, shdon, khhdon,
            tgtcthue, tgtthue
        FROM invoices
        WHERE {where_clause}
        ORDER BY tdlap ASC, shdon ASC
    """

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    
    # Process results
    items = []
    total_incoming_amount = 0
    total_outgoing_amount = 0
    total_incoming_tax = 0
    total_outgoing_tax = 0
    
    for row in rows:
        row_dict = dict(row)
        
        # Determine if this is an incoming ('in') or outgoing ('out') invoice for the user's company
        # For simplicity, if the logged-in user can access this invoice, we'll determine type based on 
        # which tax code matches the user's companies
        user_repo = UserRepository(conn)
        user_companies = user_repo.get_user_companies(current_user.id)
        user_tax_codes = [comp['tax_code'] for comp in user_companies]
        
        invoice_type = 'out' if row_dict['nbmst'] in user_tax_codes else 'in'
        
        # Calculate amounts based on invoice type
        amount = float(row_dict['tgtcthue'] or 0)
        tax_amount = float(row_dict['tgtthue'] or 0)
        
        if invoice_type == 'out':
            # For outgoing invoices, amounts are negative
            amount = -amount
            tax_amount = -tax_amount
        
        item = InvoiceFlowReportItem(
            id=row_dict['id'],
            date=row_dict['tdlap'][:10] if row_dict['tdlap'] else '',
            type=invoice_type,
            company_name=row_dict['nmten'] if invoice_type == 'in' else row_dict['nbten'],
            tax_code=row_dict['nmmst'] if invoice_type == 'in' else row_dict['nbmst'],
            amount=amount,
            tax_amount=tax_amount,
            invoice_number=str(row_dict['shdon']) if row_dict['shdon'] else '',
            invoice_symbol=row_dict['khhdon'] or ''
        )
        
        items.append(item)
        
        # Update totals
        if invoice_type == 'in':
            total_incoming_amount += abs(amount)  # Using abs because incoming amounts are positive
            total_incoming_tax += abs(tax_amount)
        else:
            total_outgoing_amount += abs(amount)  # Using abs because outgoing amounts are stored as negative
            total_outgoing_tax += abs(tax_amount)
    
    # Calculate net tax obligation (what the company owes = outgoing tax - incoming tax)
    net_tax_obligation = total_outgoing_tax - total_incoming_tax
    
    return InvoiceFlowReportResponse(
        items=items,
        total_incoming_amount=total_incoming_amount,
        total_outgoing_amount=total_outgoing_amount,
        total_incoming_tax=total_incoming_tax,
        total_outgoing_tax=total_outgoing_tax,
        net_tax_obligation=net_tax_obligation
    )


@router.get("/vat-timeline", response_model=VATTaxTimelineResponse)
async def get_vat_timeline_report(
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    tax_code: Optional[str] = Query(None, description="Filter by company tax code"),
    current_user: UserAuth = Depends(get_current_user),
    conn = Depends(get_db),
):
    """
    Get VAT tax timeline showing incoming vs outgoing taxes over time.
    """
    # Build base query conditions
    conditions = []
    params = []

    if from_date:
        conditions.append("tdlap >= %s")
        params.append(from_date.isoformat())
    if to_date:
        conditions.append("tdlap <= %s")
        params.append(to_date.isoformat() + "T23:59:59")
    
    # For non-admin users, restrict access to assigned companies
    company_clause, company_params = build_company_restriction_clause(
        current_user.id, current_user.role, conn, "nbmst", "nmmst"
    )
    conditions.append(company_clause)
    params.extend(company_params)
    
    # If specific tax code is provided, add it to the condition
    if tax_code:
        conditions.append("(nbmst = %s OR nmmst = %s)")
        params.extend([tax_code, tax_code])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Simpler approach - get all invoices and classify them in Python
    query = f"""
        SELECT
            i.tdlap, i.nbmst, i.nmmst, i.tgtthue
        FROM invoices i
        WHERE {where_clause}
        ORDER BY i.tdlap ASC
    """
    
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    
    # Get user's company tax codes to determine incoming vs outgoing
    user_repo = UserRepository(conn)
    user_companies = user_repo.get_user_companies(current_user.id)
    user_tax_codes = [comp['tax_code'] for comp in user_companies]
    
    # Group by date and calculate incoming vs outgoing taxes
    date_data: Dict[str, Dict[str, float]] = {}
    
    for row in rows:
        row_dict = dict(row)
        date_str = row_dict['tdlap'][:10] if row_dict['tdlap'] else None
        if not date_str:
            continue
            
        tax_amount = float(row_dict['tgtthue'] or 0)
        
        if date_str not in date_data:
            date_data[date_str] = {'incoming_tax': 0, 'outgoing_tax': 0}
        
        # Determine if this is incoming or outgoing for user's companies
        if row_dict['nbmst'] in user_tax_codes:
            # This is an outgoing invoice (sale) for the user's company
            date_data[date_str]['outgoing_tax'] += tax_amount
        elif row_dict['nmmst'] in user_tax_codes:
            # This is an incoming invoice (purchase) for the user's company
            date_data[date_str]['incoming_tax'] += tax_amount
    
    # Convert to response format
    items = []
    total_incoming_tax = 0
    total_outgoing_tax = 0
    
    for date_str, data in date_data.items():
        incoming_tax = data['incoming_tax']
        outgoing_tax = data['outgoing_tax']
        net_tax = outgoing_tax - incoming_tax  # Amount owed (positive) or credit (negative)
        
        item = VATTaxTimelineItem(
            date=date_str,
            incoming_tax=incoming_tax,
            outgoing_tax=outgoing_tax,
            net_tax=net_tax
        )
        
        items.append(item)
        total_incoming_tax += incoming_tax
        total_outgoing_tax += outgoing_tax
    
    net_tax_obligation = total_outgoing_tax - total_incoming_tax
    
    return VATTaxTimelineResponse(
        items=items,
        total_incoming_tax=total_incoming_tax,
        total_outgoing_tax=total_outgoing_tax,
        net_tax_obligation=net_tax_obligation
    )