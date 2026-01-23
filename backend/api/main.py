"""
Invoice API Server - Main Entry Point

FastAPI server providing REST API for invoice data.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_database, close_connection
from backend.api.routes import invoices_router, companies_router, collector_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_database()
    yield
    # Shutdown
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


# Include routers
app.include_router(invoices_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(collector_router, prefix="/api")

