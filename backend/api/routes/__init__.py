"""Routes package."""
from .invoices import router as invoices_router
from .companies import router as companies_router
from .collector import router as collector_router
from .auth import router as auth_router
from .logs import router as logs_router
from .users import router as users_router
from .reports import router as reports_router
from .schedule import router as schedule_router

__all__ = ["invoices_router", "companies_router", "collector_router", "auth_router", "logs_router", "users_router", "reports_router", "schedule_router"]

