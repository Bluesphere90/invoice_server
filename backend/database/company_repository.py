"""
Company Repository - CRUD for companies table.
Matches existing schema with: tax_code, company_name, username, password
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CompanyRepository:
    """
    Manages company credentials for multi-company invoice collection.
    """

    def __init__(self, conn):
        self.conn = conn

    def get_active_companies(self) -> List[Dict[str, Any]]:
        """Get all active companies for collecting."""
        sql = """
        SELECT id, tax_code, company_name, username, password
        FROM companies
        WHERE is_active = TRUE
        ORDER BY id
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        
        return [dict(row) for row in rows] if rows else []

    def get_company_by_tax_code(self, tax_code: str) -> Optional[Dict[str, Any]]:
        """Get company by tax code."""
        sql = "SELECT * FROM companies WHERE tax_code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (tax_code,))
            row = cur.fetchone()
        
        return dict(row) if row else None

    def get_company_with_password(self, tax_code: str) -> Optional[Dict[str, Any]]:
        """Get company by tax code including password (for collector jobs)."""
        sql = "SELECT id, tax_code, company_name, username, password FROM companies WHERE tax_code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (tax_code,))
            row = cur.fetchone()
        
        return dict(row) if row else None

    def add_company(
        self,
        tax_code: str,
        username: str,
        password: str,
        company_name: str = ""
    ) -> int:
        """Add a new company."""
        sql = """
        INSERT INTO companies (tax_code, company_name, username, password)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (tax_code, company_name, username, password))
            company_id = cur.fetchone()['id']
        self.conn.commit()
        
        logger.info(f"Added company {tax_code} with id {company_id}")
        return company_id

    def update_last_sync(self, tax_code: str, error: str = None):
        """Update last sync timestamp and error."""
        # Note: Schema doesn't have last_sync_at/last_error columns yet
        # Just update updated_at for now
        sql = "UPDATE companies SET updated_at = now() WHERE tax_code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (tax_code,))
        self.conn.commit()
        
        if error:
            logger.warning(f"Sync for {tax_code} completed with error: {error}")

    def set_active(self, tax_code: str, is_active: bool):
        """Enable/disable a company."""
        sql = "UPDATE companies SET is_active = %s WHERE tax_code = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (is_active, tax_code))
        self.conn.commit()

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Get all companies (active and inactive)."""
        sql = """
        SELECT id, tax_code, company_name, username, is_active, 
               created_at, updated_at
        FROM companies
        ORDER BY id
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        
        return [dict(row) for row in rows] if rows else []

    def update_company(self, tax_code: str, **kwargs):
        """Update company fields."""
        allowed_fields = ['company_name', 'username', 'password', 'is_active']
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs and kwargs[field] is not None:
                updates.append(f"{field} = %s")
                values.append(kwargs[field])
        
        if not updates:
            return
        
        values.append(tax_code)
        sql = f"UPDATE companies SET {', '.join(updates)}, updated_at = now() WHERE tax_code = %s"
        
        with self.conn.cursor() as cur:
            cur.execute(sql, values)
        self.conn.commit()

    def deactivate_company(self, tax_code: str):
        """Soft delete by setting is_active = FALSE."""
        self.set_active(tax_code, False)

