"""SCO requires a fresh challenge per page and attempt. No live requests or messages."""
import json
import logging
import unittest
from datetime import date
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

import requests
from backend.collector.http.client import (
    HoaDonHttpClient, GdtRequestError, GdtAuthenticationBlockedError,
)
from backend.collector.http.endpoints import BASE_URL
from backend.collector.invoice.list_service import InvoiceListService


def response(status=200, payload=None, text=None):
    result = requests.Response()
    result.status_code = status
    result._content = (json.dumps(payload) if text is None else text).encode()
    result.headers["Content-Type"] = "application/json"
    result.url = BASE_URL + "/test"
    result.request = requests.Request("GET", result.url).prepare()
    return result


class ScoCaptchaTests(unittest.TestCase):
    def setUp(self):
        self.http = HoaDonHttpClient()
        self.addCleanup(self.http.session.close)
        self.http._wait_for_request_slot = MagicMock()
        self.http._log_response = MagicMock()
        self.sleep = patch("backend.collector.http.client.time.sleep").start()
        self.solver = patch("backend.collector.http.client.SvgCaptchaSolver").start()
        self.solver.return_value.solve.return_value = "solved-value"
        self.addCleanup(patch.stopall)
        self.http.session.request = MagicMock()
        self.counter = 0
        self.lookups = []
        self.lookup_results = []

    def handle_request(self, method, url, **kwargs):
        if urlsplit(url).path.endswith("/captcha"):
            self.counter += 1
            return response(payload={"key": f"challenge-{self.counter}", "svg": "<svg/>"})
        self.lookups.append((url, kwargs))
        pair = kwargs.get("params", {})
        if not pair.get("ckey") or not pair.get("cvalue"):
            return response(500, {"message": "Required request parameter 'ckey' is not present"})
        if self.lookup_results:
            value = self.lookup_results.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return response(payload={"datas": [], "state": None})

    def collect(self, purchase=True):
        self.http.session.request.side_effect = self.handle_request
        service = InvoiceListService(self.http, MagicMock())
        service.fetch_invoice_identifiers("test-tax", date(2026, 10, 1), date(2026, 10, 1), purchase)
        return service

    def test_purchase_and_sold_send_challenge_in_query_and_headers(self):
        for direction in ("purchase", "sold"):
            with self.subTest(direction=direction):
                self.http.session.request.side_effect = self.handle_request
                self.http.request("GET", BASE_URL + f"/sco-query/invoices/{direction}",
                                  response_kind="list", max_attempts=1)
                url, kwargs = self.lookups[-1]
                for key in ("ckey", "cvalue"):
                    self.assertEqual(kwargs["params"][key], kwargs["headers"][key])
                self.assertEqual("/tra-cuu/tra-cuu-hoa-don", kwargs["headers"]["End-Point"])
                self.http._wait_for_request_slot.assert_called_with(3)
        self.assertEqual(2, self.counter)

    def test_every_pagination_page_gets_another_challenge(self):
        def routed(method, url, **kwargs):
            if "/query/invoices/" in urlsplit(url).path:
                return response(payload={"datas": []})
            if "/sco-query/" in url:
                self.lookup_results = [response(payload={
                    "datas": [], "state": "next-page" if len(self.lookups) == 0 else None,
                })]
            return self.handle_request(method, url, **kwargs)
        self.http.session.request.side_effect = routed
        service = InvoiceListService(self.http, MagicMock())
        service.fetch_invoice_identifiers("test-tax", date(2026, 10, 1), date(2026, 10, 1), True)
        self.assertEqual(2, len(self.lookups))
        self.assertEqual(2, self.counter)
        self.assertNotEqual(self.lookups[0][1]["params"]["ckey"], self.lookups[1][1]["params"]["ckey"])
        self.assertEqual(["next-page"], parse_qs(urlsplit(self.lookups[1][0]).query)["state"])
        self.assertNotIn("ckey", parse_qs(urlsplit(self.lookups[1][0]).query))
        self.assertEqual(3, service.successful_response_count)

    def test_retry_refreshes_challenge_and_keeps_one_lookup_budget(self):
        self.http.session.request.side_effect = self.handle_request
        self.lookup_results = [response(503), requests.ReadTimeout(), response(payload={"datas": []})]
        self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=3,
                          response_kind="list")
        self.assertEqual(3, self.counter)
        self.assertEqual(["challenge-1", "challenge-2", "challenge-3"],
                         [kwargs["params"]["ckey"] for _, kwargs in self.lookups])
        self.assertEqual(6, self.http.session.request.call_count)
        self.assertEqual(2, self.sleep.call_count)

    def test_captcha_fetch_failures_share_bounded_budget(self):
        self.http.session.request.return_value = response(503)
        with self.assertRaisesRegex(GdtRequestError, "3 attempts"):
            self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=3)
        self.assertEqual(3, self.http.session.request.call_count)
        self.assertEqual(2, self.sleep.call_count)
        self.solver.assert_not_called()

    def test_captcha_rejection_gets_a_fresh_challenge(self):
        self.http.session.request.side_effect = self.handle_request
        self.lookup_results = [response(400, {"message": "Captcha invalid"}),
                               response(payload={"datas": []})]
        self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=2)
        self.assertEqual(2, self.counter)
        self.assertEqual(2, len(self.lookups))

    def test_other_400_is_not_retried_or_misreported_as_empty(self):
        self.http.session.request.side_effect = self.handle_request
        self.lookup_results = [response(400, {"message": "Invalid date range"})]
        with self.assertRaisesRegex(GdtRequestError, "HTTP 400"):
            self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=3)
        self.assertEqual(1, len(self.lookups))
        self.sleep.assert_not_called()

    def test_behavior_block_during_captcha_stops_immediately(self):
        self.http.session.request.return_value = response(403, {"message": "Hệ thống phát hiện hành vi không hợp lệ"})
        with self.assertRaises(GdtAuthenticationBlockedError):
            self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=3)
        self.assertEqual(1, self.http.session.request.call_count)
        self.sleep.assert_not_called()

    def test_unsolved_captcha_never_sends_lookup_or_leaks_challenge(self):
        self.http.session.request.side_effect = self.handle_request
        self.solver.return_value.solve.return_value = ""
        with self.assertRaisesRegex(GdtRequestError, "could not be solved") as caught:
            self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", max_attempts=2)
        self.assertEqual(2, self.counter)
        self.assertEqual([], self.lookups)
        self.assertNotIn("challenge-", str(caught.exception))

    def test_standard_queries_details_and_foreign_hosts_do_not_fetch_captcha(self):
        self.http.session.request.return_value = response(payload={"datas": []})
        for url in [BASE_URL + "/query/invoices/purchase", BASE_URL + "/sco-query/invoices/detail",
                    "https://other.example/api/sco-query/invoices/purchase"]:
            self.http.request("GET", url, max_attempts=1)
        self.solver.assert_not_called()
        self.assertEqual(3, self.http.session.request.call_count)
        for call in self.http.session.request.call_args_list:
            self.assertNotIn("params", call.kwargs)

    def test_stale_challenge_removed_without_mutating_caller_params(self):
        self.http.session.request.side_effect = self.handle_request
        params = {"ckey": "old-key", "cvalue": "old-value", "size": 15}
        self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase?state=next&ckey=stale&cvalue=stale",
                          params=params, max_attempts=1)
        url, kwargs = self.lookups[0]
        self.assertEqual({"state": ["next"]}, parse_qs(urlsplit(url).query))
        self.assertEqual("challenge-1", kwargs["params"]["ckey"])
        self.assertEqual("old-key", params["ckey"])
        self.assertEqual(15, kwargs["params"]["size"])

    def test_lookup_request_id_is_restored_after_fetching_captcha(self):
        self.http.session.request.side_effect = self.handle_request
        self.http.request("GET", BASE_URL + "/sco-query/invoices/purchase", request_profile="lookup", max_attempts=1)
        self.assertEqual(self.lookups[0][1]["headers"]["Request-Id"], self.http.last_request_id)
        self.assertEqual("lookup", self.http.last_request_profile)

    def test_response_logs_redact_challenge_values(self):
        self.http._log_response = HoaDonHttpClient._log_response.__get__(self.http)
        value = response(payload={})
        value.url = BASE_URL + "/sco-query/invoices/purchase?ckey=private-key&cvalue=private-answer&size=15"
        with self.assertLogs("backend.collector.http.client", logging.INFO) as logs:
            self.http._log_response(value, "lookup")
        self.assertNotIn("private-key", str(logs.output))
        self.assertNotIn("private-answer", str(logs.output))
        self.assertIn("size=15", str(logs.output))
