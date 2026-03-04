"""
User repository for database operations.
"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, conn):
        self.conn = conn

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        sql = """
        SELECT id, username, password_hash, full_name, role, 
               is_active, is_locked, failed_login_attempts, last_login,
               created_at, updated_at
        FROM users 
        WHERE username = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (username,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        sql = """
        SELECT id, username, password_hash, full_name, role, 
               is_active, is_locked, failed_login_attempts, last_login,
               created_at, updated_at
        FROM users 
        WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_user(
        self,
        username: str,
        password_hash: str,
        full_name: str = None,
        role: str = "user"
    ) -> Dict[str, Any]:
        """Create a new user."""
        sql = """
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id, username, full_name, role, is_active, created_at
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (username, password_hash, full_name, role))
            row = cur.fetchone()
            self.conn.commit()
            logger.info(f"Created user: {username}")
            return dict(row)

    def update_login_success(self, user_id: int):
        """Update user on successful login."""
        sql = """
        UPDATE users 
        SET last_login = CURRENT_TIMESTAMP,
            failed_login_attempts = 0,
            is_locked = FALSE
        WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            self.conn.commit()

    def increment_failed_login(self, user_id: int, max_attempts: int = 5):
        """Increment failed login attempts and lock if exceeded."""
        sql = """
        UPDATE users 
        SET failed_login_attempts = failed_login_attempts + 1,
            is_locked = CASE 
                WHEN failed_login_attempts + 1 >= %s THEN TRUE 
                ELSE is_locked 
            END
        WHERE id = %s
        RETURNING is_locked
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (max_attempts, user_id))
            row = cur.fetchone()
            self.conn.commit()
            return row['is_locked'] if row else False

    def unlock_user(self, user_id: int):
        """Unlock a user account."""
        sql = """
        UPDATE users 
        SET is_locked = FALSE, failed_login_attempts = 0
        WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            self.conn.commit()
            logger.info(f"Unlocked user ID: {user_id}")

    def update_password(self, user_id: int, password_hash: str):
        """Update user password."""
        sql = """
        UPDATE users 
        SET password_hash = %s
        WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (password_hash, user_id))
            self.conn.commit()

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (without password hash)."""
        sql = """
        SELECT id, username, full_name, role, is_active, is_locked,
               last_login, created_at, updated_at
        FROM users
        ORDER BY created_at DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    # =====================================================
    # USER-COMPANY PERMISSIONS
    # =====================================================

    def get_user_companies(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all companies a user has access to."""
        sql = """
        SELECT c.id, c.tax_code, c.company_name, uc.access_level
        FROM user_companies uc
        JOIN companies c ON c.id = uc.company_id
        WHERE uc.user_id = %s AND c.is_active = TRUE
        ORDER BY c.company_name
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [dict(row) for row in cur.fetchall()]

    def user_has_company_access(
        self, 
        user_id: int, 
        company_id: int,
        required_level: str = None
    ) -> bool:
        """Check if user has access to a specific company."""
        if required_level:
            sql = """
            SELECT 1 FROM user_companies 
            WHERE user_id = %s AND company_id = %s AND access_level = %s
            """
            params = (user_id, company_id, required_level)
        else:
            sql = """
            SELECT 1 FROM user_companies 
            WHERE user_id = %s AND company_id = %s
            """
            params = (user_id, company_id)
            
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None

    def assign_company_to_user(
        self,
        user_id: int,
        company_id: int,
        access_level: str = "read"
    ):
        """Assign a company to a user."""
        sql = """
        INSERT INTO user_companies (user_id, company_id, access_level)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, company_id) 
        DO UPDATE SET access_level = EXCLUDED.access_level
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id, company_id, access_level))
            self.conn.commit()
            logger.info(f"Assigned company {company_id} to user {user_id} with {access_level} access")

    def remove_company_from_user(self, user_id: int, company_id: int):
        """Remove a company assignment from a user."""
        sql = """
        DELETE FROM user_companies 
        WHERE user_id = %s AND company_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_id, company_id))
            self.conn.commit()

    def get_company_users(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all users with access to a specific company."""
        sql = """
        SELECT u.id, u.username, u.full_name, u.role, uc.access_level
        FROM user_companies uc
        JOIN users u ON u.id = uc.user_id
        WHERE uc.company_id = %s AND u.is_active = TRUE
        ORDER BY u.username
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (company_id,))
            return [dict(row) for row in cur.fetchall()]
