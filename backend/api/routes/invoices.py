"""Invoice API routes."""
from typing import Optional
from datetime import date
import io
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend.database import get_db
from backend.api.schemas import (
    InvoiceSummary, 
    InvoiceDetail, 
    InvoiceItemResponse,
    InvoiceListResponse,
    InvoiceStatsResponse,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def build_invoice_where_clause(from_date, to_date, tax_code, buyer_tax_code, search):
    """Build WHERE clause and params for invoice queries."""
    conditions = []
    params = []
    
    if from_date:
        conditions.append("tdlap >= %s")
        params.append(from_date.isoformat())
        
    if to_date:
        conditions.append("tdlap <= %s")
        params.append(to_date.isoformat() + "T23:59:59")
        
    if tax_code:
        conditions.append("nbmst = %s")
        params.append(tax_code)
        
    if buyer_tax_code:
        conditions.append("nmmst = %s")
        params.append(buyer_tax_code)
        
    if search:
        conditions.append("(nbten ILIKE %s OR nmten ILIKE %s OR CAST(shdon AS TEXT) LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    tax_code: Optional[str] = Query(None, description="Filter by seller tax code (nbmst)"),
    buyer_tax_code: Optional[str] = Query(None, description="Filter by buyer tax code (nmmst)"),
    search: Optional[str] = Query(None, description="Search in invoice number or company name"),
    conn = Depends(get_db),
):
    """
    List invoices with pagination and filters.
    """
    offset = (page - 1) * size
    
    where_clause, params = build_invoice_where_clause(from_date, to_date, tax_code, buyer_tax_code, search)
    
    # Count total
    count_sql = f"SELECT COUNT(*) as count FROM invoices WHERE {where_clause}"
    
    # Fetch data
    data_sql = f"""
        SELECT id, nbmst, nbten, nmmst, nmten, shdon, khhdon, khmshdon, 
               tdlap, tgtcthue, tgtthue, tgtttbso, tthai
        FROM invoices 
        WHERE {where_clause}
        ORDER BY tdlap DESC NULLS LAST, shdon DESC NULLS LAST
        LIMIT %s OFFSET %s
    """
    
    with conn.cursor() as cur:
        # Get total count
        cur.execute(count_sql, params if params else None)
        count_row = cur.fetchone()
        total = count_row['count'] if isinstance(count_row, dict) else count_row[0]
        
        # Get data with pagination
        data_params = params + [size, offset]
        cur.execute(data_sql, data_params)
        rows = cur.fetchall()
    
    # Rows are already dicts from RealDictCursor
    items = [InvoiceSummary(**dict(row)) for row in rows]
    pages = (total + size - 1) // size if total > 0 else 1
    
    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/export")
async def export_invoices_excel(
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    tax_code: Optional[str] = Query(None, description="Filter by seller tax code (nbmst)"),
    buyer_tax_code: Optional[str] = Query(None, description="Filter by buyer tax code (nmmst)"),
    search: Optional[str] = Query(None, description="Search in invoice number or company name"),
    conn = Depends(get_db),
):
    """
    Export invoices to Excel file.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl not installed")
    
    where_clause, params = build_invoice_where_clause(from_date, to_date, tax_code, buyer_tax_code, search)
    
    # Fetch all matching data (no pagination for export)
    data_sql = f"""
        SELECT nbmst, nbten, nmmst, nmten, shdon, khhdon, khmshdon, 
               tdlap, tgtcthue, tgtthue, tgtttbso, tthai
        FROM invoices 
        WHERE {where_clause}
        ORDER BY tdlap DESC NULLS LAST, shdon DESC NULLS LAST
    """
    
    with conn.cursor() as cur:
        cur.execute(data_sql, params if params else None)
        rows = cur.fetchall()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Hóa đơn"
    
    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="6C5CE7", end_color="6C5CE7", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = [
        "STT", "Ngày lập", "Số HĐ", "Ký hiệu", "Mẫu số",
        "MST Người bán", "Tên Người bán",
        "MST Người mua", "Tên Người mua",
        "Tiền chưa thuế", "Tiền thuế", "Tổng tiền", "Trạng thái"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Data rows
    for row_idx, row in enumerate(rows, 2):
        data = dict(row)
        ws.cell(row=row_idx, column=1, value=row_idx - 1).border = thin_border
        ws.cell(row=row_idx, column=2, value=data.get('tdlap', '')[:10] if data.get('tdlap') else '').border = thin_border
        ws.cell(row=row_idx, column=3, value=data.get('shdon', '')).border = thin_border
        ws.cell(row=row_idx, column=4, value=data.get('khhdon', '')).border = thin_border
        ws.cell(row=row_idx, column=5, value=data.get('khmshdon', '')).border = thin_border
        ws.cell(row=row_idx, column=6, value=data.get('nbmst', '')).border = thin_border
        ws.cell(row=row_idx, column=7, value=data.get('nbten', '')).border = thin_border
        ws.cell(row=row_idx, column=8, value=data.get('nmmst', '')).border = thin_border
        ws.cell(row=row_idx, column=9, value=data.get('nmten', '')).border = thin_border
        ws.cell(row=row_idx, column=10, value=float(data.get('tgtcthue') or 0)).border = thin_border
        ws.cell(row=row_idx, column=11, value=float(data.get('tgtthue') or 0)).border = thin_border
        ws.cell(row=row_idx, column=12, value=float(data.get('tgtttbso') or 0)).border = thin_border
        ws.cell(row=row_idx, column=13, value=data.get('tthai', '')).border = thin_border
    
    # Auto-size columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Generate filename with date range
    filename = f"hoadon_{from_date or 'all'}_{to_date or 'all'}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/stats", response_model=InvoiceStatsResponse)
async def get_stats(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    conn = Depends(get_db),
):
    """
    Get invoice statistics for dashboard.
    """
    # Build date filter
    conditions = []
    params = []
    
    if from_date:
        conditions.append("tdlap >= %s")
        params.append(from_date.isoformat())
    if to_date:
        conditions.append("tdlap <= %s")
        params.append(to_date.isoformat() + "T23:59:59")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with conn.cursor() as cur:
        # Total counts
        cur.execute(f"""
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(tgtcthue), 0) as total_amount,
                COALESCE(SUM(tgtthue), 0) as total_tax
            FROM invoices
            WHERE {where_clause}
        """, params if params else None)
        
        row = cur.fetchone()
        total_invoices = row['total']
        total_amount = float(row['total_amount']) if row['total_amount'] else 0.0
        total_tax = float(row['total_tax']) if row['total_tax'] else 0.0
        
        # Invoices by month (extract year-month from tdlap string)
        cur.execute(f"""
            SELECT 
                SUBSTRING(tdlap FROM 1 FOR 7) as month,
                COUNT(*) as cnt
            FROM invoices
            WHERE tdlap IS NOT NULL AND {where_clause}
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """, params if params else None)
        
        by_month = {r['month']: r['cnt'] for r in cur.fetchall() if r['month']}
    
    return InvoiceStatsResponse(
        total_invoices=total_invoices,
        total_purchase=0,
        total_sold=0,
        total_amount=total_amount,
        total_tax=total_tax,
        invoices_by_month=by_month,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: str,
    conn = Depends(get_db),
):
    """
    Get single invoice with items.
    """
    with conn.cursor() as cur:
        # Get invoice header
        cur.execute("""
            SELECT id, nbmst, nbten, nmmst, nmten, shdon, khhdon, khmshdon,
                   tdlap, tgtcthue, tgtthue, tgtttbso, tthai,
                   nbdchi, nmdchi, dvtte, tgtttbchu, htttoan
            FROM invoices
            WHERE id = %s
        """, (invoice_id,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        invoice_data = dict(row)
        
        # Get items
        cur.execute("""
            SELECT id, idhdon, stt, ten, dvtinh, sluong, dgia, thtien, tsuat
            FROM invoice_items
            WHERE idhdon = %s
            ORDER BY stt
        """, (invoice_id,))
        
        items = [InvoiceItemResponse(**dict(r)) for r in cur.fetchall()]
    
    invoice_data["items"] = items
    return InvoiceDetail(**invoice_data)
