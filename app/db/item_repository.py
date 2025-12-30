class InvoiceItemRepository:
    """
    Mirror SQLite InvoiceItems table (FULL).
    """

    def __init__(self, conn):
        self.conn = conn

    def upsert_item(self, item: dict):
        columns = []
        values = []
        updates = []

        for k in item.keys():
            columns.append(k)
            values.append(f"%({k})s")
            updates.append(f"{k} = EXCLUDED.{k}")

        sql = f"""
        INSERT INTO InvoiceItems (
            {", ".join(columns)}
        )
        VALUES (
            {", ".join(values)}
        )
        ON CONFLICT (id) DO UPDATE SET
            {", ".join(updates)}
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, item)

        self.conn.commit()
