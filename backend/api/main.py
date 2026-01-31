"""
Invoice API Server - Main Entry Point

FastAPI server providing REST API for invoice data.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import init_database, close_connection
from backend.api.routes import invoices_router, companies_router, collector_router, auth_router
from backend.api.auth import get_current_user
from backend.observability.telegram import TelegramNotifier
from backend.observability.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_database()
    
    # Send startup notification
    notifier = TelegramNotifier()
    notifier.send_startup_notification("Invoice API")
    
    yield
    
    # Shutdown
    notifier.send_shutdown_notification("Invoice API")
    close_connection()


app = FastAPI(
    title="Invoice API",
    description="API for invoice management system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler - send critical errors to Telegram
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions and notify via Telegram."""
    logger.exception(f"Uncaught exception: {exc}")
    
    # Send to Telegram (only for server errors, not 4xx)
    notifier = TelegramNotifier()
    notifier.send_error_alert(
        error_type="API Uncaught Exception",
        message_text=str(exc),
        context={
            "path": str(request.url.path),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Invoice API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENV
    }


@app.post("/api/admin/test-telegram")
async def test_telegram(
    current_user: dict = Depends(get_current_user)
):
    """Send a test message to Telegram. Admin only."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")
    
    notifier = TelegramNotifier()
    success = notifier.send_message(
        "🧪 <b>Test Message</b>\n\n"
        "Telegram integration is working correctly!\n"
        f"Triggered by: {current_user.get('username', 'unknown')}"
    )
    
    return {
        "success": success,
        "message": "Test message sent" if success else "Failed to send message"
    }


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(invoices_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(collector_router, prefix="/api")
