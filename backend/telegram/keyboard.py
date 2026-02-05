"""
Telegram Inline Keyboard Utilities

Build inline keyboard markups for interactive bot flows.
"""
from typing import List, Dict, Any, Optional


def build_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
    """
    Build inline keyboard markup.
    
    Args:
        buttons: 2D list of button dicts with 'text' and 'callback_data' keys
        
    Returns:
        Telegram InlineKeyboardMarkup dict
    """
    return {
        "inline_keyboard": buttons
    }


def build_company_keyboard(companies: List[Dict[str, Any]], prefix: str = "company") -> Dict[str, Any]:
    """
    Build keyboard for company selection.
    
    Args:
        companies: List of company dicts with 'tax_code' and 'company_name'
        prefix: Callback data prefix
        
    Returns:
        InlineKeyboardMarkup with company buttons (2 per row)
    """
    buttons = []
    row = []
    
    for i, company in enumerate(companies[:10]):  # Max 10 companies
        name = company.get('company_name', company.get('tax_code', 'N/A'))
        # Truncate name to fit button
        display_name = name[:20] + "..." if len(name) > 20 else name
        
        row.append({
            "text": display_name,
            "callback_data": f"{prefix}:{company['tax_code']}"
        })
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    return build_inline_keyboard(buttons)


def build_invoice_type_keyboard(tax_code: str) -> Dict[str, Any]:
    """
    Build keyboard for invoice type selection (Vào/Ra).
    """
    buttons = [
        [
            {"text": "📥 Hóa đơn Vào (Mua)", "callback_data": f"type:{tax_code}:in"},
            {"text": "📤 Hóa đơn Ra (Bán)", "callback_data": f"type:{tax_code}:out"}
        ]
    ]
    return build_inline_keyboard(buttons)


def build_date_range_keyboard(tax_code: str, inv_type: str) -> Dict[str, Any]:
    """
    Build keyboard for date range selection.
    """
    buttons = [
        [
            {"text": "7 ngày", "callback_data": f"range:{tax_code}:{inv_type}:7"},
            {"text": "30 ngày", "callback_data": f"range:{tax_code}:{inv_type}:30"},
        ],
        [
            {"text": "Tháng này", "callback_data": f"range:{tax_code}:{inv_type}:month"},
            {"text": "Tháng trước", "callback_data": f"range:{tax_code}:{inv_type}:last_month"},
        ]
    ]
    return build_inline_keyboard(buttons)


def build_pagination_keyboard(
    current_page: int, 
    total_pages: int, 
    callback_prefix: str
) -> Dict[str, Any]:
    """
    Build pagination keyboard.
    """
    buttons = []
    row = []
    
    if current_page > 1:
        row.append({"text": "◀ Trước", "callback_data": f"{callback_prefix}:{current_page - 1}"})
    
    row.append({"text": f"Trang {current_page}/{total_pages}", "callback_data": "noop"})
    
    if current_page < total_pages:
        row.append({"text": "Sau ▶", "callback_data": f"{callback_prefix}:{current_page + 1}"})
    
    buttons.append(row)
    return build_inline_keyboard(buttons)


def build_collector_company_keyboard(companies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build keyboard for collector company selection.
    """
    buttons = []
    row = []
    
    for i, company in enumerate(companies[:8]):  # Max 8 companies
        name = company.get('company_name', company.get('tax_code', 'N/A'))
        display_name = name[:18] + ".." if len(name) > 18 else name
        
        row.append({
            "text": display_name,
            "callback_data": f"collect_co:{company['tax_code']}"
        })
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Add "All companies" button
    buttons.append([{"text": "🔄 Tất cả công ty", "callback_data": "collect_co:all"}])
    
    return build_inline_keyboard(buttons)


def build_collector_date_keyboard(tax_code: str) -> Dict[str, Any]:
    """
    Build keyboard for collector date range selection.
    """
    buttons = [
        [
            {"text": "7 ngày (mặc định)", "callback_data": f"collect_run:{tax_code}:7"},
            {"text": "30 ngày", "callback_data": f"collect_run:{tax_code}:30"},
        ],
        [
            {"text": "Hôm nay", "callback_data": f"collect_run:{tax_code}:1"},
            {"text": "Tháng này", "callback_data": f"collect_run:{tax_code}:month"},
        ]
    ]
    return build_inline_keyboard(buttons)
