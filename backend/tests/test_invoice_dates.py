"""Regression tests for invoice calendar dates; PostgreSQL tests are read-only.

Set INVOICE_TEST_DATABASE_URL to run SQL checks against a test database.
Every SQL test uses VALUES fixtures, never inserts or changes invoice data.
"""
import os
import unittest
from datetime import date

from backend.core.date_utils import to_vn_date_str, vn_date_sql, build_vn_date_filter


class VietnamDateTests(unittest.TestCase):
    def test_utc_midnight_boundary_is_next_vietnam_date(self):
        self.assertEqual("2026-10-01", to_vn_date_str("2026-09-30T17:00:00Z"))

    def test_naive_and_date_only_are_local(self):
        for value in ("2026-10-01", "2026-10-01T00:00:00", "2026-10-01T00:00:00+07:00"):
            with self.subTest(value=value):
                self.assertEqual("2026-10-01", to_vn_date_str(value))

    def test_column_names_cannot_inject_sql(self):
        for columns in ((), ("tdlap; DROP TABLE invoices",), ("COALESCE(nky,tdlap)",)):
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                vn_date_sql(*columns)


@unittest.skipUnless(os.getenv("INVOICE_TEST_DATABASE_URL"), "Requires PostgreSQL test URL")
class VietnamDateSqlTests(unittest.TestCase):
    def setUp(self):
        import psycopg2
        self.conn = psycopg2.connect(os.environ["INVOICE_TEST_DATABASE_URL"])
        self.conn.set_session(readonly=True)
        self.cur = self.conn.cursor()

    def tearDown(self):
        self.conn.rollback()
        self.cur.close()
        self.conn.close()

    def evaluate(self, signed, issued):
        self.cur.execute(
            f"SELECT {vn_date_sql('nky', 'tdlap')} "
            "FROM (VALUES (%s::text, %s::text)) AS fixture(nky, tdlap)",
            (signed, issued),
        )
        return self.cur.fetchone()[0]

    def test_dates_are_independent_of_database_timezone(self):
        cases = (
            (None, "2026-09-30T17:00:00Z", date(2026, 10, 1)),
            ("", "2026-09-30T17:00:00Z", date(2026, 10, 1)),
            ("  ", "2026-09-30T17:00:00Z", date(2026, 10, 1)),
            ("2026-10-02T17:00:00Z", "2026-09-30T17:00:00Z", date(2026, 10, 3)),
            (None, "2026-10-01T00:00:00+07:00", date(2026, 10, 1)),
            (None, "2026-10-01T00:00:00", date(2026, 10, 1)),
            (None, "2026-10-01", date(2026, 10, 1)),
            (None, "2026-12-31T17:00:00Z", date(2027, 1, 1)),
            (None, None, None),
        )
        for zone in ("UTC", "Asia/Ho_Chi_Minh", "America/Los_Angeles"):
            self.cur.execute("SET LOCAL TIME ZONE %s", (zone,))
            for signed, issued, expected in cases:
                with self.subTest(zone=zone, signed=signed, issued=issued):
                    self.assertEqual(expected, self.evaluate(signed, issued))

    def test_inclusive_single_day_and_month_end(self):
        fixtures = (
            ("before", "2026-09-30T16:59:59.999999Z"),
            ("start", "2026-09-30T17:00:00Z"),
            ("end", "2026-10-01T16:59:59.999999Z"),
            ("next", "2026-10-01T17:00:00Z"),
        )
        conditions, bounds = build_vn_date_filter(date(2026, 10, 1), date(2026, 10, 1), "tdlap")
        self.cur.execute(
            "SELECT label FROM (VALUES " + ",".join(["(%s,%s::text)"] * len(fixtures)) +
            ") AS fixture(label,tdlap) WHERE " + " AND ".join(conditions) + " ORDER BY label",
            [value for row in fixtures for value in row] + bounds,
        )
        self.assertEqual([("end",), ("start",)], self.cur.fetchall())

    def test_open_bounds_and_issuance_month(self):
        for lower, upper, expected in (
            (date(2026, 10, 1), None, 1),
            (None, date(2026, 9, 30), 0),
            (None, None, 1),
        ):
            conditions, bounds = build_vn_date_filter(lower, upper, "tdlap")
            self.cur.execute(
                "SELECT count(*) FROM (VALUES ('2026-09-30T17:00:00Z'::text)) fixture(tdlap) "
                "WHERE " + (" AND ".join(conditions) or "TRUE"), bounds,
            )
            self.assertEqual(expected, self.cur.fetchone()[0])
        self.cur.execute(
            f"SELECT TO_CHAR({vn_date_sql('tdlap')}, 'YYYY-MM') "
            "FROM (VALUES ('2026-09-30T17:00:00Z'::text)) fixture(tdlap)"
        )
        self.assertEqual("2026-10", self.cur.fetchone()[0])

    def test_invoice_route_preserves_company_filters(self):
        from backend.api.routes.invoices import build_invoice_where_clause
        clause, params = build_invoice_where_clause(
            date(2026, 10, 1), date(2026, 10, 1), "0102617088", "0111321270", None
        )
        self.cur.execute(
            "SELECT count(*) FROM (VALUES "
            "(NULL::text,'2026-09-30T17:00:00Z'::text,'0102617088','0111321270'),"
            "(NULL::text,'2026-09-30T17:00:00Z'::text,'0102617088','other-buyer')) "
            "AS fixture(nky,tdlap,nbmst,nmmst) WHERE " + clause,
            params,
        )
        self.assertEqual(1, self.cur.fetchone()[0])


if __name__ == "__main__":
    unittest.main()
