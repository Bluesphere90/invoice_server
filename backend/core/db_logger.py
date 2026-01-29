"""
Database logging handler.
Stores log records in PostgreSQL system_logs table.
"""
import logging
import json
import threading
from datetime import datetime
from typing import Optional
from queue import Queue

from backend.database.connection import get_connection


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes logs to PostgreSQL.
    Uses a background thread to avoid blocking the main application.
    """

    def __init__(self, level=logging.INFO, batch_size: int = 10, flush_interval: float = 5.0):
        super().__init__(level)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: Queue = Queue()
        self._shutdown = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def emit(self, record: logging.LogRecord):
        """Queue log record for async insertion."""
        try:
            log_entry = self._format_record(record)
            self._queue.put(log_entry)
        except Exception:
            self.handleError(record)

    def _format_record(self, record: logging.LogRecord) -> dict:
        """Convert LogRecord to dictionary for database insertion."""
        metadata = {}
        
        # Add exception info if present
        if record.exc_info:
            metadata["exception"] = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
        
        # Add extra fields if present
        for key in ["user_id", "request_path", "company_id", "invoice_id"]:
            if hasattr(record, key):
                metadata[key] = getattr(record, key)
        
        return {
            "timestamp": datetime.fromtimestamp(record.created),
            "level": record.levelname,
            "logger": record.name[:100],  # Truncate to column size
            "message": record.getMessage()[:2000],  # Limit message size
            "user_id": getattr(record, "user_id", None),
            "request_path": getattr(record, "request_path", None),
            "metadata": metadata if metadata else None
        }

    def _worker(self):
        """Background worker to batch insert logs."""
        batch = []
        
        while not self._shutdown.is_set():
            try:
                # Collect logs up to batch_size or timeout
                while len(batch) < self.batch_size:
                    try:
                        entry = self._queue.get(timeout=self.flush_interval)
                        batch.append(entry)
                        self._queue.task_done()
                    except:
                        break  # Timeout, flush what we have
                
                if batch:
                    self._flush_batch(batch)
                    batch = []
                    
            except Exception as e:
                # Log to stderr if DB logging fails
                import sys
                print(f"DatabaseLogHandler error: {e}", file=sys.stderr)
                batch = []

    def _flush_batch(self, batch: list):
        """Insert batch of logs into database."""
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                for entry in batch:
                    metadata_json = json.dumps(entry["metadata"], ensure_ascii=False) if entry["metadata"] else None
                    cur.execute(
                        """
                        INSERT INTO system_logs (timestamp, level, logger, message, user_id, request_path, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            entry["timestamp"],
                            entry["level"],
                            entry["logger"],
                            entry["message"],
                            entry["user_id"],
                            entry["request_path"],
                            metadata_json
                        )
                    )
                conn.commit()
        except Exception as e:
            import sys
            print(f"Failed to flush logs to database: {e}", file=sys.stderr)
            try:
                conn.rollback()
            except:
                pass

    def close(self):
        """Gracefully shutdown the handler."""
        self._shutdown.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        
        # Flush remaining logs
        remaining = []
        while not self._queue.empty():
            try:
                remaining.append(self._queue.get_nowait())
            except:
                break
        
        if remaining:
            self._flush_batch(remaining)
        
        super().close()


def setup_database_logging(level=logging.INFO, loggers: list = None):
    """
    Setup database logging for specified loggers.
    
    Args:
        level: Minimum log level to capture
        loggers: List of logger names to attach handler to. 
                 If None, attaches to root logger.
    """
    handler = DatabaseLogHandler(level=level)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    
    if loggers is None:
        # Attach to root logger
        logging.getLogger().addHandler(handler)
    else:
        for logger_name in loggers:
            logging.getLogger(logger_name).addHandler(handler)
    
    return handler
