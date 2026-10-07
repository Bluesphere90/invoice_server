"""Date formatting helpers for invoice timestamps."""
from datetime import date, datetime
import re
from typing import Optional, Union
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def vn_date_sql(*columns: str) -> str:
    """SQL date in Vietnam, using the first nonempty trusted column.

    Offset timestamps describe an instant; timestamps without an offset and
    date-only values already describe local Vietnam time. Never depend on the
    PostgreSQL session timezone. Column names are application constants.
    """
    if not columns or any(
        not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", column)
        for column in columns
    ):
        raise ValueError("Expected trusted SQL column names")
    values = [f"NULLIF(BTRIM({column}), '')" for column in columns]
    value = values[0] if len(values) == 1 else f"COALESCE({', '.join(values)})"
    return (
        f"(CASE WHEN {value} ~ '(Z|[+-][0-9]{{2}}:?[0-9]{{2}})$' "
        f"THEN ({value}::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh')::date "
        f"ELSE {value}::timestamp::date END)"
    )


def build_vn_date_filter(from_date: Optional[date], to_date: Optional[date], *columns: str):
    """Inclusive local-calendar date bounds for invoice SQL queries."""
    expression = vn_date_sql(*columns)
    conditions, params = [], []
    if from_date is not None:
        conditions.append(f"{expression} >= %s")
        params.append(from_date)
    if to_date is not None:
        conditions.append(f"{expression} <= %s")
        params.append(to_date)
    return conditions, params


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

