"""Cron schedule schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CronScheduleResponse(BaseModel):
    id: int
    name: str
    cron_expression: str
    description: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class CronScheduleUpdate(BaseModel):
    cron_expression: str
    description: Optional[str] = None
    is_active: Optional[bool] = None
