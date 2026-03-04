"""
System Logs API Routes.
Provides endpoints for viewing and managing system logs stored in PostgreSQL.
Admin only access.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.api.auth import get_current_user, UserAuth, require_admin
from backend.database.connection import get_cursor
from backend.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Log entry response model."""
    id: int
    timestamp: str
    level: str
    logger: Optional[str]
    message: Optional[str]
    user_id: Optional[int]
    request_path: Optional[str]
    metadata: Optional[dict]


class LogsResponse(BaseModel):
    """Paginated logs response."""
    total: int
    logs: list[LogEntry]
    page: int
    page_size: int
    total_pages: int


class LogStats(BaseModel):
    """Log statistics."""
    total_logs: int
    warning_count: int
    error_count: int
    critical_count: int
    oldest_log: Optional[str]
    newest_log: Optional[str]


@router.get("", response_model=LogsResponse)
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level (WARNING, ERROR, CRITICAL)"),
    logger_name: Optional[str] = Query(None, alias="logger", description="Filter by logger name"),
    search: Optional[str] = Query(None, description="Search in message"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=200, description="Items per page"),
    current_user: UserAuth = Depends(require_admin)
):
    """
    Get system logs. Admin only.
    
    Supports filtering by:
    - level: WARNING, ERROR, CRITICAL
    - logger: Logger name (partial match)
    - search: Text search in message
    - from_date / to_date: Date range
    """
    # Admin only check handled by Depends(require_admin)
    
    # Build query
    conditions = []
    params = []
    
    if level:
        conditions.append("level = %s")
        params.append(level.upper())
    
    if logger_name:
        conditions.append("logger ILIKE %s")
        params.append(f"%{logger_name}%")
    
    if search:
        conditions.append("message ILIKE %s")
        params.append(f"%{search}%")
    
    if from_date:
        conditions.append("timestamp >= %s")
        params.append(from_date)
    
    if to_date:
        conditions.append("timestamp <= %s::date + INTERVAL '1 day'")
        params.append(to_date)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_cursor() as cur:
        # Get total count
        cur.execute(f"SELECT COUNT(*) as count FROM system_logs WHERE {where_clause}", params)
        total = cur.fetchone()["count"]
        
        # Get paginated results
        offset = (page - 1) * page_size
        cur.execute(
            f"""
            SELECT id, timestamp, level, logger, message, user_id, request_path, metadata
            FROM system_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset]
        )
        rows = cur.fetchall()
    
    logs = [
        LogEntry(
            id=row["id"],
            timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
            level=row["level"],
            logger=row["logger"],
            message=row["message"],
            user_id=row["user_id"],
            request_path=row["request_path"],
            metadata=row["metadata"]
        )
        for row in rows
    ]
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return LogsResponse(
        total=total,
        logs=logs,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=LogStats)
async def get_log_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to include in stats"),
    current_user: UserAuth = Depends(require_admin)
):
    """Get log statistics. Admin only."""
    # Check handled by dependency
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE level = 'WARNING') as warning_count,
                COUNT(*) FILTER (WHERE level = 'ERROR') as error_count,
                COUNT(*) FILTER (WHERE level = 'CRITICAL') as critical_count,
                MIN(timestamp) as oldest_log,
                MAX(timestamp) as newest_log
            FROM system_logs
            WHERE timestamp >= %s
            """,
            (cutoff_date,)
        )
        row = cur.fetchone()
    
    return LogStats(
        total_logs=row["total"],
        warning_count=row["warning_count"],
        error_count=row["error_count"],
        critical_count=row["critical_count"],
        oldest_log=row["oldest_log"].isoformat() if row["oldest_log"] else None,
        newest_log=row["newest_log"].isoformat() if row["newest_log"] else None
    )


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=7, le=365, description="Delete logs older than this many days"),
    current_user: UserAuth = Depends(require_admin)
):
    """
    Delete old logs. Admin only.
    Keeps logs from the last N days.
    """
    # Check handled by dependency
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM system_logs WHERE timestamp < %s",
            (cutoff_date,)
        )
        deleted_count = cur.rowcount
    
    logger.info(f"Cleaned up {deleted_count} old logs (older than {days} days)")
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }
