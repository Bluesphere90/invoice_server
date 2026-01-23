"""
Invoice Item Repository for storing invoice line items.
"""
import json
import logging

logger = logging.getLogger(__name__)


def _normalize_value(val):
    """
    Normalize value for PostgreSQL insertion.
    Converts complex types (dict, list) to JSON strings.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val


class InvoiceItemRepository:
    """
    Repository for invoice line items (hdonLquans).
    """

    def __init__(self, conn):
        self.conn = conn

    def upsert_item(self, item: dict):
        """
        Upsert a single invoice item.
        """
        # Normalize values
        normalized_item = {}
        for k, v in item.items():
            normalized_item[k] = _normalize_value(v)
        
        columns = []
        values = []
        updates = []

        for k in normalized_item.keys():
            columns.append(k)
            values.append(f"%({k})s")
            updates.append(f"{k} = EXCLUDED.{k}")

        sql = f"""
        INSERT INTO invoice_items (
            {", ".join(columns)}
        )
        VALUES (
            {", ".join(values)}
        )
        ON CONFLICT (id) DO UPDATE SET
            {", ".join(updates)}
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, normalized_item)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to upsert item: {e}")
            self.conn.rollback()
            raise
