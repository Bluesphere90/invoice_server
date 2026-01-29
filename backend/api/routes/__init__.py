"""Routes package."""
from .invoices import router as invoices_router
from .companies import router as companies_router
from .collector import router as collector_router
from .auth import router as auth_router

__all__ = ["invoices_router", "companies_router", "collector_router", "auth_router"]
