"""Dependency-isolated regressions for the timeout patch.

Loads the real source definitions. HTTP, repositories, login and notifications
are mocked at their boundaries; no connection to GDT or production is made.
"""
import ast
import logging
import random
import threading
import time
import unittest
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit

ROOT = Path(__file__).parent


class Timeout(Exception):
    pass


class ReadTimeout(Timeout):
    pass


class StripImports(ast.NodeTransformer):
    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None


def load_definitions(relative, namespace, names=None):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                 and (names is None or node.name in names)]
    tree = ast.fix_missing_locations(StripImports().visit(tree))
    exec(compile(tree, str(ROOT / relative), "exec"), namespace)
    return namespace


SETTINGS = SimpleNamespace(
    HDDT_REQUEST_DELAY_MS=0, HDDT_BROWSER_USER_AGENT="test-agent",
    HDDT_LIST_READ_TIMEOUT_SECONDS=60, HDDT_LIST_MAX_ATTEMPTS=3,
)
REQUESTS = SimpleNamespace(
    Session=MagicMock(side_effect=lambda: MagicMock()), Response=object,
    exceptions=SimpleNamespace(ConnectionError=ConnectionError, Timeout=Timeout),
)
BASE = dict(
    logging=logging, random=random, threading=threading, time=time, uuid=uuid,
    date=date, datetime=datetime, timedelta=timedelta, timezone=timezone,
    parsedate_to_datetime=parsedate_to_datetime, settings=SETTINGS,
    urlsplit=urlsplit, urlencode=urlencode, urlparse=urlparse, parse_qs=parse_qs,
    List=List, Dict=Dict, Any=Any, Optional=Optional, Tuple=Tuple, monthrange=monthrange,
    logger=MagicMock(), requests=REQUESTS,
    BASE_URL="https://example.test/api", CAPTCHA_ENDPOINT="/captcha",
    AUTH_ENDPOINT="/auth", PROFILE_ENDPOINT="/profile",
)
HTTP = load_definitions("backend/collector/http/client.py", BASE.copy())
GdtRequestError = HTTP["GdtRequestError"]
Blocked = HTTP["GdtAuthenticationBlockedError"]
HttpClient = HTTP["HoaDonHttpClient"]
LIST = load_definitions("backend/collector/invoice/list_service.py", dict(
    BASE, HoaDonHttpClient=HttpClient, GdtRequestError=GdtRequestError,
    InvoiceIdentifier=SimpleNamespace, STATUS_REFRESH_FIELDS=(),
))
ListService = LIST["InvoiceListService"]


def response(payload, status=200):
    value = MagicMock()
    value.status_code = status
    value.json.return_value = payload
    value.text = ""
    value.content = b"{}"
    value.headers = {}
    return value


def invoice(identifier):
    return dict(id=identifier, nbmst="tax", khhdon="C26MYY", shdon=1,
                khmshdon=2, tdlap="2026-10-23T00:00:00+07:00")


def gateway(sco_purchase_fails=True):
    client = HttpClient()
    client._wait_for_request_slot = MagicMock()
    client._log_response = MagicMock()

    def request(method, url, **kwargs):
        endpoint = urlsplit(url).path
        if endpoint.endswith("/sco-query/invoices/purchase") and sco_purchase_fails:
            raise ReadTimeout()
        data = []
        if endpoint.endswith("/query/invoices/purchase") and "/sco-query/" not in endpoint:
            key = "september" if "09%2F2026" in url else "october"
            data = [invoice(key)]
        if endpoint.endswith("/sco-query/invoices/sold"):
            data = [invoice("sold")]
        return response({"datas": data})

    client.session.request.side_effect = request
    return client


def repository():
    repo = MagicMock()
    repo.invoice_header_exists.return_value = False
    return repo


def workflow_bindings(client):
    service = MagicMock()
    service.fetch_profile.return_value = {"tax_code": "tax", "company_name": "Company"}
    worker = MagicMock()
    worker.process.return_value = True
    return dict(
        BASE, HoaDonHttpClient=MagicMock(return_value=client),
        LoginService=MagicMock(), SvgCaptchaSolver=MagicMock(),
        ProfileService=MagicMock(return_value=service), InvoiceListService=ListService,
        InvoiceDetailWorker=MagicMock(return_value=worker),
        InvoiceRepository=MagicMock(return_value=repository()),
        InvoiceItemRepository=MagicMock(), CompanyRepository=MagicMock(),
        HealthRecorder=MagicMock(), TelegramNotifier=MagicMock(),
        GdtAuthenticationBlockedError=Blocked, CollectorScheduleRepository=MagicMock(),
        get_connection=MagicMock(), init_database=MagicMock(),
        JobManager=MagicMock(), JobStatus=SimpleNamespace(RUNNING="running", FAILED="failed", COMPLETED="completed"),
    )


class PartialCollectionTests(unittest.TestCase):
    def setUp(self):
        mock_sleep = patch.object(time, "sleep")
        self.sleep = mock_sleep.start()
        self.addCleanup(mock_sleep.stop)

    def collect(self, client):
        namespace = workflow_bindings(client)
        load_definitions("backend/collector/main.py", namespace, {"collect_for_company"})
        result = namespace["collect_for_company"](
            {"tax_code": "tax", "username": "user", "password": "password"},
            repository(), MagicMock(), MagicMock(), MagicMock(),
            date(2026, 9, 23), date(2026, 10, 23),
        )
        return result, namespace

    def test_timeout_does_not_prevent_other_apis_or_detail_downloads(self):
        client = gateway()
        result, namespace = self.collect(client)
        self.assertFalse(result["collection_success"])
        self.assertFalse(result["list_complete"])
        self.assertEqual("partial", result["stage"])
        self.assertEqual(4, len(result["failed_ranges"]))
        self.assertEqual(3, result["invoices_detected"])
        self.assertEqual(3, result["invoices_downloaded"])
        self.assertEqual(3, namespace["InvoiceDetailWorker"].return_value.process.call_count)
        bad_calls = [call for call in client.session.request.call_args_list
                     if "/sco-query/invoices/purchase?" in call.args[1]]
        self.assertEqual(3, len(bad_calls))
        for call in bad_calls:
            self.assertEqual((10, 60), call.kwargs["timeout"])
            self.assertNotIn("max_attempts", call.kwargs)
        self.assertEqual(2, self.sleep.call_count)
        self.assertEqual(8, result["list_responses"])

    def test_healthy_empty_ranges_are_still_complete(self):
        client = gateway(False)
        client.session.request.side_effect = lambda *a, **kw: response({"datas": []})
        result, _ = self.collect(client)
        self.assertTrue(result["collection_success"])
        self.assertTrue(result["list_complete"])
        self.assertEqual([], result["failed_ranges"])
        self.assertEqual(12, result["list_responses"])

    def test_strict_mode_keeps_raising_on_incomplete_ranges(self):
        service = ListService(gateway(), repository())
        with self.assertRaises(GdtRequestError):
            service.fetch_invoice_identifiers("tax", date(2026, 10, 23), date(2026, 10, 23), True)
        self.assertEqual([], service.failed_ranges)

    def test_completed_pages_remain_available_when_later_page_times_out(self):
        client = gateway(False)
        client.session.request.side_effect = [response({"datas": [invoice("first")], "state": "next"})] + [ReadTimeout()] * 3
        repo = repository()
        service = ListService(client, repo)
        result = service._fetch_one_period("tax", date(2026, 10, 1), date(2026, 10, 23), True, False, True, set(), allow_partial=True)
        self.assertEqual(["first"], [item.id for item in result])
        repo.upsert_invoice_summary.assert_called_once()
        self.assertEqual(1, len(service.failed_ranges))
        self.assertEqual(1, service.successful_response_count)

    def test_behavior_block_still_stops_the_entire_run(self):
        client = gateway()
        client.session.request.return_value = response({"message": "Hệ thống phát hiện hành vi không hợp lệ."}, status=403)
        client.session.request.side_effect = None
        result, namespace = self.collect(client)
        self.assertTrue(result["auth_blocked"])
        self.assertFalse(result["collection_success"])
        self.assertEqual(1, client.session.request.call_count)
        namespace["InvoiceDetailWorker"].assert_not_called()

    def test_persistence_failure_is_not_hidden_as_an_api_outage(self):
        repo = repository()
        repo.upsert_invoice_summary.side_effect = RuntimeError("database failure")
        service = ListService(gateway(False), repo)
        with self.assertRaisesRegex(RuntimeError, "database failure"):
            service.fetch_invoice_identifiers("tax", date(2026, 10, 23), date(2026, 10, 23), True, allow_partial=True)
        self.assertEqual([], service.failed_ranges)

    def test_next_run_retries_previously_failed_ranges(self):
        failed_service = ListService(gateway(), repository())
        failed_service.fetch_invoice_identifiers("tax", date(2026, 10, 23), date(2026, 10, 23), True, allow_partial=True)
        next_service = ListService(gateway(False), repository())
        next_service.fetch_invoice_identifiers("tax", date(2026, 10, 23), date(2026, 10, 23), True, allow_partial=True)
        self.assertEqual([], next_service.failed_ranges)
        self.assertEqual(2, next_service.successful_response_count)

    def test_manual_job_downloads_available_details_but_is_not_completed(self):
        namespace = workflow_bindings(gateway())
        load_definitions("backend/collector/job_manager.py", namespace, {"run_collector_job"})
        namespace["run_collector_job"]("job", {"tax_code": "tax", "username": "user", "password": "password"}, date(2026, 9, 23), date(2026, 10, 23))
        statuses = [call.kwargs.get("status") for call in namespace["JobManager"].return_value.update_job.call_args_list]
        self.assertIn("failed", statuses)
        self.assertNotIn("completed", statuses)
        self.assertEqual(3, namespace["InvoiceDetailWorker"].return_value.process.call_count)
        namespace["TelegramNotifier"].return_value.send_job_completed.assert_not_called()

    def test_request_budget_is_validated_before_any_request(self):
        for value in [0, -1, 6, True, "3"]:
            client = gateway()
            with self.subTest(value=value), self.assertRaises(ValueError):
                client.request("GET", "https://example.test", max_attempts=value)
            client.session.request.assert_not_called()

    def test_report_shows_downloads_without_claiming_complete_coverage(self):
        namespace = dict(BASE, escape=escape, httpx=SimpleNamespace())
        load_definitions("backend/observability/telegram.py", namespace, {"TelegramNotifier"})
        notifier = object.__new__(namespace["TelegramNotifier"])
        notifier.send_message = MagicMock()
        notifier._format_timestamp = MagicMock(return_value="test")
        notifier.send_collector_result([dict(
            tax_code="tax", collection_success=False, login_success=True,
            list_complete=False, list_responses=6, invoices_detected=3,
            invoices_downloaded=3, error="lookup incomplete",
        )], 1)
        text = notifier.send_message.call_args.args[0]
        self.assertIn("0 OK, 1 lỗi", text)
        self.assertIn("3 phát hiện, 3 tải", text)
        self.assertIn("chưa đủ phạm vi tra cứu", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
