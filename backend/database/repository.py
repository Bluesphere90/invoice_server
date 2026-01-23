import logging
from datetime import datetime
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

# Columns that exist in database schema
# Note: CamelCase columns like hdonLquans, hdTrung, isHDTrung are stored with quotes
KNOWN_COLUMNS: Set[str] = {
    # Core fields
    'id', 'nbmst', 'khmshdon', 'khhdon', 'shdon', 'tdlap', 'nbten', 'nmten',
    'tgtcthue', 'tgtthue', 'tthai', 'ttxly',
    
    # Additional fields
    'cqt', 'cttkhac', 'dvtte', 'hdon', 'hsgcma', 'hsgoc', 'hthdon', 'htttoan',
    'idtbao', 'khdon', 'khhdgoc', 'khmshdgoc', 'lhdgoc', 'mhdon', 'mtdiep',
    'mtdtchieu', 'nbdchi', 'chma', 'chten', 'nbhdktngay', 'nbhdktso', 'nbhdso',
    'nblddnbo', 'nbptvchuyen', 'nbstkhoan', 'nbtnhang', 'nbtnvchuyen', 'nbttkhac',
    'ncma', 'ncnhat', 'ngcnhat', 'nky', 'nmdchi', 'nmmst', 'nmstkhoan', 'nmtnhang',
    'nmtnmua', 'nmttkhac', 'ntao', 'ntnhan', 'pban', 'ptgui', 'shdgoc', 'tchat',
    'tgia', 'tgtttbchu', 'tgtttbso', 'thdon', 'thlap', 'thttlphi', 'thttltsuat',
    'tlhdon', 'ttcktmai', 'ttkhac', 'tttbao', 'ttttkhac', 'tvandnkntt', 'mhso',
    'ladhddt', 'mkhang', 'nbsdthoai', 'nbdctdtu', 'nbfax', 'nbwebsite', 'nbcks',
    'nmsdthoai', 'nmdctdtu', 'nmcmnd', 'nmcks', 'bhphap', 'hddunlap', 'gchdgoc',
    'tbhgtngay', 'bhpldo', 'bhpcbo', 'bhpngay', 'tdlhdgoc', 'tgtphi', 'unhiem',
    'mstdvnunlhdon', 'tdvnunlhdon', 'nbmdvqhnsach', 'nbsqdinh', 'nbncqdinh',
    'nbcqcqdinh', 'nbhtban', 'nmmdvqhnsach', 'nmddvchden', 'nmtgvchdtu',
    'nmtgvchdden', 'nbtnban', 'dcdvnunlhdon', 'dksbke', 'dknlbke', 'thtttoan',
    'msttcgp', 'cqtcks', 'gchu', 'kqcht', 'hdntgia', 'tgtkcthue', 'tgtkhac',
    'nmshchieu', 'nmnchchieu', 'nmnhhhchieu', 'nmqtich', 'ktkhthue', 'qrcode',
    'ttmstten', 'ladhddtten', 'hdxkhau', 'hdxkptquan', 'hdgktkhthue',
    
    # CamelCase columns (using exact case)
    'hdonLquans', 'hdTrung', 'isHDTrung',
    
    # New columns from Detail API
    'nmstttoan', 'nmttttoan', 'hdcttchinh', 'dlhquan', 'dlnhtmai', 'bltphi',
    'tthdclquan', 'pdndungs', 'hdtbssrses',
}

# Columns that need to be quoted in SQL (camelCase)
QUOTED_COLUMNS: Set[str] = {'hdonLquans', 'hdTrung', 'isHDTrung'}


class InvoiceRepository:
    """
    PostgreSQL repository – stores invoice data with exact API column names.
    """

    MAX_DETAIL_RETRY = 30

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
    # UPSERT SUMMARY
    # =====================================================

    def upsert_invoice_summary(self, inv: Dict[str, Any]):
        """
        Save invoice data with exact column names from API.
        """
        # Filter to only known columns (keep original case)
        filtered_inv = {k: v for k, v in inv.items() if k in KNOWN_COLUMNS}

        columns = []
        placeholders = []
        updates = []

        for k in filtered_inv.keys():
            # Quote camelCase columns for PostgreSQL
            col_name = f'"{k}"' if k in QUOTED_COLUMNS else k
            columns.append(col_name)
            placeholders.append(f"%({k})s")
            updates.append(f"{col_name} = EXCLUDED.{col_name}")

        sql = f"""
        INSERT INTO invoices (
            {", ".join(columns)},
            last_downloaded_date
        )
        VALUES (
            {", ".join(placeholders)},
            now()
        )
        ON CONFLICT (id) DO UPDATE SET
            {", ".join(updates)},
            last_downloaded_date = now()
        """

        payload = {
            k: self._normalize_value(v)
            for k, v in filtered_inv.items()
        }

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, payload)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.warning(f"Failed to upsert invoice {filtered_inv.get('id')}: {e}")
            raise

    # =====================================================
    # DETAIL RETRY LOGIC
    # =====================================================

    def should_retry_detail(self, invoice_id: str) -> bool:
        sql = """
        SELECT detail_status, detail_retry_count
        FROM invoices
        WHERE id = %s
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, (invoice_id,))
            row = cur.fetchone()

        if not row:
            return True

        status = row['detail_status']
        retry = row['detail_retry_count']

        if status == 1:
            return False

        if retry is not None and retry >= self.MAX_DETAIL_RETRY:
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
                detail_status = %s,
                detail_retry_count = detail_retry_count + 1
            WHERE id = %s
            """
            params = (status, invoice_id)
        else:
            sql = """
            UPDATE invoices
            SET
                detail_status = %s,
                detail_retry_count = 0
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
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        if isinstance(value, (list, dict)):
            # Convert complex objects to JSON string
            import json
            return json.dumps(value, ensure_ascii=False)
        return str(value)
