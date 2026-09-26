"""Persistent control for automatic collector runs."""


class CollectorScheduleRepository:
    def __init__(self, conn):
        self.conn = conn

    def is_active(self) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT is_active FROM cron_schedule WHERE name = 'collector'"
            )
            row = cur.fetchone()
        return True if row is None else bool(row["is_active"])

    def disable_for_auth_block(self):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cron_schedule
                SET is_active = FALSE,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system:gdt-auth-blocked'
                WHERE name = 'collector'
                """
            )
        self.conn.commit()
