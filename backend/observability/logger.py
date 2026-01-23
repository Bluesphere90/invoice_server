"""
Centralized logging configuration.
Saves logs to storage/logs/collector.log and prints to console.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Constants
LOG_DIR = Path("storage/logs")
LOG_FILE = LOG_DIR / "collector.log"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Only configure if handlers haven't been added
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Check environment for debug mode
        if os.getenv("DEBUG", "False").lower() == "true":
            logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

        # 1. Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. File Handler
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                LOG_FILE, 
                maxBytes=MAX_BYTES, 
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}")

    return logger

def get_logger(name: str) -> logging.Logger:
    """Wrapper to ensure setup is called or just return logger."""
    # For simplicity, we just rely on the root logger configuration 
    # or per-module configuration if updated.
    # Here we can return a logger that inherits from root.
    # But to ensure our handlers are present, we can call setup_logger for the root
    # or specific loggers.
    return logging.getLogger(name)

def configure_root_logger():
    """
    Configure the root logger so all modules inherit these settings.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if os.getenv("DEBUG", "False").lower() == "true":
        root_logger.setLevel(logging.DEBUG)
        
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root_logger.addHandler(console)
    
    # File
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file.setFormatter(formatter)
        root_logger.addHandler(file)
        
        # Log startup
        root_logger.info("="*60)
        root_logger.info("Logging initialized. Writing to %s", LOG_FILE.absolute())
        root_logger.info("="*60)
        
    except Exception as e:
        root_logger.error("Failed to setup file logging: %s", e)
