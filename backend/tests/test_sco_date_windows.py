"""Regression tests for GDT's ten-day SCO limit; HTTP and repositories are mocked."""
import json
import unittest
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock

import requests
from backend.collector.http.client import HoaDonHttpClient, GdtRequestError
from backend.collector.invoice.list_service import InvoiceListService


def response(status, payload):
    value = requests.Response()
    value.status_code = status
    value._content = json.dumps(payload).encode()
    value.encoding = "utf-8"
    value.headers["Content-Type"] = "application/json"
    value.request = requests.Request("GET", "https://example.test/api").prepare()
    value.url = value.request.url
    return value


def invoice(identifier):
    return {"id": identifier, "nbmst": "test-tax", "khhdon": "C26MYY",
            "shdon": 1, "khmshdon": 2, "tdlap": "2026-10-01T00:00:00+07:00"}


class ScoDateWindowTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.override = None
        self.http = HoaDonHttpClient()
        self.addCleanup(self.http.session.close)
        self.http._wait_for_request_slot = MagicMock()
        self.http._log_response = MagicMock()
        self.http.session.request = MagicMock(side_effect=self.handle_request)
        self.repo = MagicMock()
        self.repo.invoice_header_exists.return_value = False
        self.service = InvoiceListService(self.http, self.repo)

    def handle_request(self, method, url, **kwargs):
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        terms = params["search"][0].split(";")
        start = datetime.strptime(terms[0].removeprefix("tdlap=ge="), "%d/%m/%YT%H:%M:%S")
        end = datetime.strptime(terms[1].removeprefix("tdlap=le="), "%d/%m/%YT%H:%M:%S")
        request = {"path": parsed.path, "start": start.date(), "end": end.date(),
                   "state": params.get("state", [None])[0], "params": params}
        self.requests.append(request)
        if "/sco-query/" in parsed.path and end - start >= timedelta(days=10):
            return response(400, {"message": "Khoang thoi gian tim kiem khong duoc lon hon 10 ngay."})
        if self.override:
            result = self.override(request)
            if result is not None:
                return result
        return response(200, {"datas": [], "state": None})

    def collect(self, start, end, purchase=True):
        return self.service.fetch_invoice_identifiers("test-tax", start, end, purchase)

    def sco_requests(self):
        return [r for r in self.requests if "/sco-query/" in r["path"]]

    def test_reported_september_october_range_is_accepted(self):
        self.assertEqual([], self.collect(date(2026, 9, 24), date(2026, 10, 24)))
        sco = self.sco_requests()
        self.assertEqual([
            (date(2026, 9, 24), date(2026, 9, 30)),
            (date(2026, 10, 1), date(2026, 10, 10)),
            (date(2026, 10, 11), date(2026, 10, 20)),
            (date(2026, 10, 21), date(2026, 10, 24)),
        ], [(r["start"], r["end"]) for r in sco])
        normal = [r for r in self.requests if "/query/" in r["path"]]
        self.assertEqual([
            (date(2026, 9, 24), date(2026, 9, 30)),
            (date(2026, 10, 1), date(2026, 10, 24)),
        ], [(r["start"], r["end"]) for r in normal])
        self.assertEqual(6, self.service.successful_response_count)

    def test_purchase_and_sold_have_complete_non_overlapping_coverage(self):
        cases = [
            (date(2026, 10, 1), date(2026, 10, 1)),
            (date(2026, 10, 1), date(2026, 10, 10)),
            (date(2026, 10, 1), date(2026, 10, 11)),
            (date(2026, 10, 1), date(2026, 10, 31)),
            (date(2028, 2, 1), date(2028, 2, 29)),
            (date(2026, 12, 24), date(2027, 1, 24)),
        ]
        for start, end in cases:
            for purchase in [True, False]:
                with self.subTest(start=start, end=end, purchase=purchase):
                    self.requests.clear()
                    self.collect(start, end, purchase)
                    covered = []
                    for r in self.sco_requests():
                        self.assertIn("/purchase" if purchase else "/sold", r["path"])
                        self.assertLessEqual((r["end"] - r["start"]).days + 1, 10)
                        covered.extend(r["start"] + timedelta(days=n)
                                       for n in range((r["end"] - r["start"]).days + 1))
                    expected = [start + timedelta(days=n)
                                for n in range((end-start).days+1)]
                    self.assertEqual(expected, covered)

    def test_pagination_and_deduplication_survive_range_splitting(self):
        def pages(r):
            if "/query/" in r["path"]:
                return response(200, {"datas": [invoice("shared")]})
            if r["start"] == date(2026, 10, 1):
                if r["state"] is None:
                    return response(200, {"datas": [invoice("shared")], "state": "next-page"})
                return response(200, {"datas": [invoice("page-two")]})
            return response(200, {"datas": [invoice(str(r["start"]))]})
        self.override = pages
        result = self.collect(date(2026, 10, 1), date(2026, 10, 24))
        self.assertEqual(["shared", "page-two", "2026-10-11", "2026-10-21"],
                         [item.id for item in result])
        self.assertEqual(4, self.repo.upsert_invoice_summary.call_count)
        page_two = [r for r in self.sco_requests() if r["state"] == "next-page"]
        self.assertEqual(1, len(page_two))
        self.assertEqual(date(2026, 10, 1), page_two[0]["start"])
        self.assertEqual(date(2026, 10, 10), page_two[0]["end"])
        self.assertNotIn("/api/api/", page_two[0]["path"])

    def test_real_error_in_a_later_chunk_still_fails_the_collection(self):
        def unavailable(r):
            if "/sco-query/" in r["path"] and r["start"] == date(2026, 10, 11):
                return response(400, {"message": "some other upstream validation error"})
            return None
        self.override = unavailable
        with self.assertRaisesRegex(GdtRequestError, "HTTP 400"):
            self.collect(date(2026, 10, 1), date(2026, 10, 24))
        self.assertEqual(2, self.service.successful_response_count)
        self.assertNotIn(date(2026, 10, 21), [r["start"] for r in self.sco_requests()])

    def test_same_day_and_exactly_ten_days_need_no_extra_chunk(self):
        for end in [date(2026, 10, 1), date(2026, 10, 10)]:
            self.requests.clear()
            self.collect(date(2026, 10, 1), end)
            self.assertEqual(1, len(self.sco_requests()))

    def test_query_parameters_keep_inclusive_day_boundaries(self):
        self.collect(date(2026, 10, 1), date(2026, 10, 24))
        for r in self.requests:
            self.assertEqual(["50"], r["params"]["size"])
            self.assertEqual(["tdlap:desc"], r["params"]["sort"])
            self.assertIn("T00:00:00;", r["params"]["search"][0])
            self.assertTrue(r["params"]["search"][0].endswith("T23:59:59"))

    def test_reversed_range_does_not_request_any_endpoint(self):
        self.assertEqual([], self.collect(date(2026, 10, 24), date(2026, 10, 1)))
        self.http.session.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
