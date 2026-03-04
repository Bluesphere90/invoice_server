"""
Centralized logging configuration.
Logs to console and PostgreSQL database (WARNING+ level).
"""
import logging
import sys
import os

from backend.core.db_logger import DatabaseLogHandler

# Constants
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Flag to track if root logger has been configured
_root_configured = False


def setup_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    Uses root logger configuration, so just returns the named logger.
    """
    return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """Get a logger by name. Uses root logger configuration."""
    return logging.getLogger(name)


def configure_root_logger():
    """
    Configure the root logger so all modules inherit these settings.
    - Console handler: INFO+ (or DEBUG if DEBUG env is set)
    - Database handler: WARNING+ only (to avoid database bloat)
    """
    global _root_configured
    
    if _root_configured:
        return
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if os.getenv("DEBUG", "False").lower() == "true":
        root_logger.setLevel(logging.DEBUG)
        
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 1. Console Handler - shows all logs (INFO+)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    root_logger.addHandler(console)
    
    # 2. Database Handler - only WARNING and ERROR (to avoid database bloat)
    try:
        db_handler = DatabaseLogHandler(level=logging.WARNING)
        db_handler.setFormatter(formatter)
        root_logger.addHandler(db_handler)
        root_logger.info("Database logging enabled for WARNING+ levels")
    except Exception as e:
        root_logger.warning("Failed to setup database logging: %s", e)
        root_logger.warning("Continuing with console logging only")
    
    # Log startup
    root_logger.info("=" * 60)
    root_logger.info("Logging initialized (Console + Database)")
    root_logger.info("=" * 60)
    
    _root_configured = True
