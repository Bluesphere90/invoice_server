"""Schedule API routes for admin cron management."""
import subprocess
import re
from fastapi import APIRouter, HTTPException, Depends

from backend.database import get_db
from backend.api.auth import get_current_user, UserAuth
from backend.api.schemas.cron import CronScheduleResponse, CronScheduleUpdate

router = APIRouter(prefix="/schedule", tags=["schedule"])


def validate_cron_expression(expr: str) -> bool:
    """Basic validation of cron expression (5 fields)."""
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    # Each part should contain only valid cron characters
    pattern = re.compile(r'^[\d,\-\*/]+$')
    return all(pattern.match(p) for p in parts)


@router.get("", response_model=CronScheduleResponse)
async def get_schedule(
    current_user: UserAuth = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Get the current collector cron schedule. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền xem lịch chạy")

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM cron_schedule WHERE name = 'collector'")
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Chưa có cấu hình lịch chạy")

    return CronScheduleResponse(**dict(row))


@router.put("", response_model=CronScheduleResponse)
async def update_schedule(
    update: CronScheduleUpdate,
    current_user: UserAuth = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Update the collector cron schedule. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thay đổi lịch chạy")

    if not validate_cron_expression(update.cron_expression):
        raise HTTPException(
            status_code=400,
            detail="Biểu thức cron không hợp lệ. Cần 5 trường: phút giờ ngày tháng thứ"
        )

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE cron_schedule
            SET cron_expression = %s,
                description = COALESCE(%s, description),
                is_active = COALESCE(%s, is_active),
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE name = 'collector'
            RETURNING *
        """, (
            update.cron_expression,
            update.description,
            update.is_active,
            current_user.username,
        ))
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Chưa có cấu hình lịch chạy")

    # Try to update PM2 cron_restart dynamically
    try:
        subprocess.run(
            ["pm2", "set", "invoice-collector", f"cron_restart={update.cron_expression}"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass  # Non-critical, will take effect on next PM2 restart

    return CronScheduleResponse(**dict(row))
