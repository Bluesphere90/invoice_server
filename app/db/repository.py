import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class InvoiceRepository:
    """
    PostgreSQL repository – mirror SQLite Invoices table 1–1
    """

    MAX_DETAIL_RETRY = 30  # giống C#

    def __init__(self, conn):
        self.conn = conn

    # =====================================================
    # HEADER
    # =====================================================

    def invoice_header_exists(self, invoice_id: str) -> bool:
        sql = "SELECT 1 FROM invoices WHERE id = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (invoice_id,))
            return cur.fetchone() is not None

    # =====================================================
    # UPSERT SUMMARY (FULL JSON)
    # =====================================================

    def upsert_invoice_summary(self, inv: Dict[str, Any]):
        """
        Lưu toàn bộ JSON invoice (metadata level).
        KHÔNG lọc cột – mapping trực tiếp.
        """

        columns = []
        values = []
        updates = []

        for k, v in inv.items():
            columns.append(k)
            values.append(f"%({k})s")
            updates.append(f"{k} = EXCLUDED.{k}")

        sql = f"""
        INSERT INTO invoices (
            {", ".join(columns)},
            LastDownloadedDate
        )
        VALUES (
            {", ".join(values)},
            now()
        )
        ON CONFLICT (id) DO UPDATE SET
            {", ".join(updates)},
            LastDownloadedDate = now()
        """

        payload = {
            k: self._normalize_value(v)
            for k, v in inv.items()
        }

        with self.conn.cursor() as cur:
            cur.execute(sql, payload)

        self.conn.commit()

    # =====================================================
    # DETAIL RETRY LOGIC (IDENTICAL TO C#)
    # =====================================================

    def should_retry_detail(self, invoice_id: str) -> bool:
        sql = """
        SELECT DetailStatus, DetailRetryCount
        FROM invoices
        WHERE id = %s
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, (invoice_id,))
            row = cur.fetchone()

        if not row:
            return True

        status, retry = row

        if status == 1:
            return False

        if retry >= self.MAX_DETAIL_RETRY:
            return False

        return True

    def update_detail_status(
        self,
        invoice_id: str,
        status: int,
        increment_retry: bool = False
    ):
        if increment_retry:
            sql = """
            UPDATE invoices
            SET
                DetailStatus = %s,
                DetailRetryCount = DetailRetryCount + 1
            WHERE id = %s
            """
            params = (status, invoice_id)
        else:
            sql = """
            UPDATE invoices
            SET
                DetailStatus = %s,
                DetailRetryCount = 0
            WHERE id = %s
            """
            params = (status, invoice_id)

        with self.conn.cursor() as cur:
            cur.execute(sql, params)

        self.conn.commit()

    # =====================================================
    # UTIL
    # =====================================================

    @staticmethod
    def _normalize_value(value):
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return value
        if value is None:
            return None
        return str(value)
