"""
PostgreSQL connection management.
"""
import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.config import settings

logger = logging.getLogger(__name__)

_connection = None


def get_connection():
    """Get or create database connection."""
    global _connection

    if _connection is None or _connection.closed:
        logger.info("Creating new database connection...")
        _connection = psycopg2.connect(
            settings.DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        _connection.autocommit = False
        logger.info("Database connected successfully")

    return _connection


def close_connection():
    """Close the database connection."""
    global _connection
    if _connection and not _connection.closed:
        _connection.close()
        logger.info("Database connection closed")
    _connection = None


@contextmanager
def get_cursor() -> Generator:
    """Context manager for database cursor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_database():
    """Initialize database tables if not exist."""
    from pathlib import Path

    migrations_dir = Path(__file__).parent.parent.parent / "migrations"

    with get_cursor() as cursor:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            logger.info(f"Running migration: {sql_file.name}")
            sql = sql_file.read_text()
            cursor.execute(sql)

    logger.info("Database initialization complete")
