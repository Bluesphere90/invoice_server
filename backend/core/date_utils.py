"""Date formatting helpers for invoice timestamps."""
from datetime import datetime
from typing import Optional, Union
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def to_vn_date_str(value: Optional[Union[str, datetime]]) -> str:
    """
    Convert ISO datetime (typically UTC from tax system) to Vietnam date string.
    Returns YYYY-MM-DD. Empty string when input is empty/None.
    """
    if not value:
        return ""

    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            # Fallback for unexpected formats.
            return raw[:10]

    if dt.tzinfo is None:
        return dt.date().isoformat()
    return dt.astimezone(VN_TZ).date().isoformat()

