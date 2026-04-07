"""Pydantic schemas for invoice data."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class InvoiceItemResponse(BaseModel):
    """Single invoice item (hàng hóa/dịch vụ)."""
    id: str
    idhdon: str
    stt: Optional[int] = None          # Số thứ tự
    ten: Optional[str] = None          # Tên hàng hóa
    dvtinh: Optional[str] = None       # Đơn vị tính
    sluong: Optional[float] = None     # Số lượng
    dgia: Optional[float] = None       # Đơn giá
    thtien: Optional[float] = None     # Thành tiền
    tsuat: Optional[float] = None      # Thuế suất
    
    class Config:
        from_attributes = True


class InvoiceSummary(BaseModel):
    """Invoice summary for list view."""
    id: str
    nbmst: Optional[str] = None        # Mã số thuế người bán
    nbten: Optional[str] = None        # Tên người bán
    nmmst: Optional[str] = None        # Mã số thuế người mua
    nmten: Optional[str] = None        # Tên người mua
    shdon: Optional[int] = None        # Số hóa đơn
    khhdon: Optional[str] = None       # Ký hiệu hóa đơn
    khmshdon: Optional[int] = None     # Ký hiệu mẫu số hóa đơn
    tdlap: Optional[str] = None        # Thời điểm lập
    nky: Optional[str] = None          # Ngày ký
    tgtcthue: Optional[float] = None   # Tổng giá trị chưa thuế
    tgtthue: Optional[float] = None    # Tổng giá trị thuế
    tgtttbso: Optional[float] = None   # Tổng tiền thanh toán bằng số
    tthai: Optional[int] = None        # Trạng thái
    
    class Config:
        from_attributes = True


class InvoiceDetail(InvoiceSummary):
    """Full invoice detail with items."""
    # Additional header fields
    nbdchi: Optional[str] = None       # Địa chỉ người bán
    nmdchi: Optional[str] = None       # Địa chỉ người mua
    dvtte: Optional[str] = None        # Đơn vị tiền tệ
    tgtttbchu: Optional[str] = None    # Tổng tiền bằng chữ
    htttoan: Optional[str] = None      # Hình thức thanh toán
    
    # Items
    items: List[InvoiceItemResponse] = []


class InvoiceListResponse(BaseModel):
    """Paginated invoice list response."""
    items: List[InvoiceSummary]
    total: int
    page: int
    size: int
    pages: int


class InvoiceStatsResponse(BaseModel):
    """Dashboard statistics."""
    total_invoices: int
    total_purchase: int
    total_sold: int
    total_amount: float
    total_tax: float
    invoices_by_month: dict
