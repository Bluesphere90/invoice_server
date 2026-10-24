"""Collector failures must never become empty, successful results. No live HTTP or messages."""
import json
import logging
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from backend.collector.http.client import (
    HoaDonHttpClient, GdtRequestError, GdtAuthenticationBlockedError,
)
from backend.collector.invoice.list_service import InvoiceListService
from backend.collector.invoice.detail_worker import InvoiceDetailWorker
from backend.observability.telegram import TelegramNotifier


def response(status=200, payload=None, text=None, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = (text if text is not None else json.dumps(payload)).encode()
    result.encoding = "utf-8"
    result.headers.update(headers or {"Content-Type": "application/json"})
    result.request = requests.Request("GET", "https://example.test/api").prepare()
    result.url = result.request.url
    result.close = MagicMock()
    return result


class GatewayRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.client = HoaDonHttpClient()
        self.addCleanup(self.client.session.close)
        self.client._wait_for_request_slot = MagicMock()
        self.client._log_response = MagicMock()
        self.client.session.request = MagicMock()
        self.sleep_patch = patch("backend.collector.http.client.time.sleep")
        self.sleep = self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    def test_html_200_then_valid_captcha_recovers(self):
        self.client.session.request.side_effect = [
            response(text="<html>Error</html>", headers={"Content-Type": "text/html"}),
            response(payload={"key": "key", "svg": "<svg/>"}),
        ]
        self.assertEqual({"key": "key", "svg": "<svg/>"}, self.client.get_captcha())
        self.assertEqual(2, self.client.session.request.call_count)
        self.assertEqual(1, self.sleep.call_count)
        calls = self.client.session.request.call_args_list
        self.assertNotEqual(calls[0].kwargs["headers"]["Request-Id"], calls[1].kwargs["headers"]["Request-Id"])

    def test_auth_html_200_can_recover(self):
        self.client.session.request.side_effect = [response(text="<html>Error</html>"), response(payload={"token": "token"})]
        self.assertEqual("token", self.client.authenticate("user", "password", "captcha", "key")["token"])
        self.assertEqual(2, self.client.session.request.call_count)

    def test_exhausted_html_is_bounded_and_does_not_leak_body(self):
        self.client.session.request.return_value = response(text="<html>secret-test-marker</html>", headers={"Content-Type": "text/html"})
        with self.assertLogs("backend.collector.http.client", logging.WARNING) as logs:
            with self.assertRaises(GdtRequestError) as caught:
                self.client.get_captcha()
        self.assertEqual(5, self.client.session.request.call_count)
        self.assertEqual(4, self.sleep.call_count)
        message = str(caught.exception)
        self.assertIn("captcha", message)
        self.assertIn("HTML", message)
        self.assertIn("HTTP 200", message)
        self.assertIn("request_id=", message)
        self.assertNotIn("secret-test-marker", message + str(logs.output))

    def test_empty_response_is_reported_and_retried(self):
        self.client.session.request.return_value = response(text="")
        with self.assertRaisesRegex(GdtRequestError, "empty response"):
            self.client.get_captcha()
        self.assertEqual(5, self.client.session.request.call_count)

    def test_503_timeout_then_success_share_one_budget(self):
        self.client.session.request.side_effect = [response(503), requests.Timeout(), response(payload={"datas": []})]
        service = InvoiceListService(self.client, MagicMock())
        self.assertEqual({"datas": []}, service._fetch_with_retry("https://example.test/list"))
        self.assertEqual(3, self.client.session.request.call_count)
        self.assertEqual(1, service.successful_response_count)

    def test_exhausted_list_never_returns_none_or_empty_success(self):
        self.client.session.request.return_value = response(503)
        service = InvoiceListService(self.client, MagicMock())
        with self.assertRaisesRegex(GdtRequestError, "3 attempts"):
            service._fetch_with_retry("https://example.test/list")
        self.assertEqual(3, self.client.session.request.call_count)
        self.assertEqual(0, service.successful_response_count)

    def test_error_object_is_not_an_empty_invoice_list(self):
        self.client.session.request.return_value = response(payload={"message": "upstream failed"})
        service = InvoiceListService(self.client, MagicMock())
        with self.assertRaisesRegex(GdtRequestError, "datas"):
            service._fetch_with_retry("https://example.test/list")
        self.assertEqual(0, service.successful_response_count)
        service.repo.upsert_invoice_summary.assert_not_called()

    def test_pagination_failure_does_not_return_partial_success(self):
        self.client.session.request.side_effect = [response(payload={"datas": [], "state": "next"})] + [response(503)] * 5
        service = InvoiceListService(self.client, MagicMock())
        with self.assertRaises(GdtRequestError):
            service.fetch_invoice_identifiers("tax", date(2026, 10, 21), date(2026, 10, 21), True)
        self.assertEqual(4, self.client.session.request.call_count)
        self.assertEqual(1, service.successful_response_count)

    def test_bad_credentials_are_not_retried(self):
        self.client.session.request.return_value = response(401, payload={"message": "invalid credentials"})
        with self.assertRaisesRegex(GdtRequestError, "HTTP 401"):
            self.client.authenticate("user", "password", "captcha", "key")
        self.assertEqual(1, self.client.session.request.call_count)
        self.sleep.assert_not_called()

    def test_token_missing_is_not_retried(self):
        self.client.session.request.return_value = response(payload={"message": "invalid captcha"})
        with self.assertRaisesRegex(GdtRequestError, "token missing"):
            self.client.authenticate("user", "password", "captcha", "key")
        self.assertEqual(1, self.client.session.request.call_count)

    def test_behavior_block_is_not_retried(self):
        self.client.session.request.return_value = response(403, payload={"message": "Hệ thống phát hiện hành vi không hợp lệ."})
        with self.assertRaises(GdtAuthenticationBlockedError):
            self.client.get_captcha()
        self.assertEqual(1, self.client.session.request.call_count)
        self.sleep.assert_not_called()

    def test_retry_after_is_honored(self):
        self.client.session.request.side_effect = [response(429, headers={"Retry-After": "17"}), response(payload={})]
        self.client.request("GET", "https://example.test/list")
        self.sleep.assert_called_once_with(17)

    def test_invalid_retry_after_uses_backoff(self):
        self.client.session.request.side_effect = [response(429, headers={"Retry-After": "soon"}), response(payload={})]
        self.client.request("GET", "https://example.test/list")
        self.assertGreaterEqual(self.sleep.call_args.args[0], 5)

    def test_long_retry_after_stops_until_later_run(self):
        self.client.session.request.return_value = response(429, headers={"Retry-After": "120"})
        with self.assertRaisesRegex(GdtRequestError, "later collector run"):
            self.client.request("GET", "https://example.test/list")
        self.assertEqual(1, self.client.session.request.call_count)
        self.sleep.assert_not_called()

    @patch("backend.collector.invoice.detail_worker.build_invoice_detail_url", return_value="https://example.test/detail")
    def test_detail_has_one_retry_budget_and_one_failure_record(self, _url):
        self.client.session.request.return_value = response(text="<html>Error</html>")
        repo = MagicMock()
        worker = InvoiceDetailWorker(self.client, repo, MagicMock())
        with self.assertRaises(GdtRequestError):
            worker.process(SimpleNamespace(id="invoice"))
        self.assertEqual(5, self.client.session.request.call_count)
        repo.update_detail_status.assert_called_once_with("invoice", status=-1, increment_retry=True)
        repo.upsert_invoice_summary.assert_not_called()

    @patch("backend.collector.invoice.detail_worker.build_invoice_detail_url", return_value="https://example.test/detail")
    def test_detail_save_failure_does_not_redownload(self, _url):
        self.client.session.request.return_value = response(payload={"id": "invoice", "hdhhdvu": []})
        repo = MagicMock()
        repo.upsert_invoice_summary.side_effect = RuntimeError("database failure")
        with self.assertRaisesRegex(RuntimeError, "database failure"):
            InvoiceDetailWorker(self.client, repo, MagicMock()).process(SimpleNamespace(id="invoice"))
        self.assertEqual(1, self.client.session.request.call_count)
        repo.update_detail_status.assert_called_once_with("invoice", status=-1, increment_retry=True)

    @patch("backend.collector.invoice.detail_worker.build_invoice_detail_url", return_value="https://example.test/detail")
    def test_wrong_detail_id_is_not_saved(self, _url):
        self.client.session.request.return_value = response(payload={"id": "another", "hdhhdvu": []})
        repo = MagicMock()
        with self.assertRaisesRegex(GdtRequestError, "does not match"):
            InvoiceDetailWorker(self.client, repo, MagicMock()).process(SimpleNamespace(id="invoice"))
        repo.upsert_invoice_summary.assert_not_called()


class ResultAccuracyTests(unittest.TestCase):
    def setUp(self):
        with patch("backend.observability.logger.configure_root_logger"):
            from backend.collector import main
        self.main = main
        self.patches = []
        for name in ["HoaDonHttpClient", "SvgCaptchaSolver", "LoginService", "ProfileService", "InvoiceListService", "InvoiceDetailWorker"]:
            p = patch.object(main, name)
            self.patches.append(p)
            setattr(self, name, p.start().return_value)
            self.addCleanup(p.stop)
        self.ProfileService.fetch_profile.return_value = {"tax_code": "tax", "company_name": "Company"}
        self.InvoiceListService.fetch_invoice_identifiers.side_effect = [[], []]
        self.InvoiceListService.successful_response_count = 4
        self.InvoiceDetailWorker.process.return_value = True

    def collect(self):
        return self.main.collect_for_company(
            {"tax_code": "tax", "username": "user", "password": "password"},
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), date(2026, 10, 21), date(2026, 10, 21),
        )

    def test_login_success_list_error_is_failed_result(self):
        self.InvoiceListService.fetch_invoice_identifiers.side_effect = GdtRequestError("HTML response")
        result = self.collect()
        self.assertTrue(result["login_success"])
        self.assertFalse(result["collection_success"])
        self.assertFalse(result["list_complete"])
        self.assertEqual("purchase_list", result["stage"])
        self.assertIn("HTML", result["error"])
        self.HoaDonHttpClient.session.close.assert_called_once()

    def test_successful_empty_lists_are_a_complete_run(self):
        result = self.collect()
        self.assertTrue(result["collection_success"])
        self.assertTrue(result["list_complete"])
        self.assertEqual("completed", result["stage"])
        self.assertIsNone(result["error"])

    def test_partial_detail_failure_is_not_success(self):
        self.InvoiceListService.fetch_invoice_identifiers.side_effect = [[SimpleNamespace(id="invoice")], []]
        self.InvoiceDetailWorker.process.side_effect = GdtRequestError("failed detail")
        result = self.collect()
        self.assertFalse(result["collection_success"])
        self.assertTrue(result["list_complete"])
        self.assertEqual(1, result["download_failed"])
        self.assertIn("retry", result["error"])

    def test_detail_behavior_block_stops_instead_of_skipping(self):
        self.InvoiceListService.fetch_invoice_identifiers.side_effect = [[SimpleNamespace(id="one"), SimpleNamespace(id="two")], []]
        self.InvoiceDetailWorker.process.side_effect = GdtAuthenticationBlockedError("blocked", "id", "detail")
        result = self.collect()
        self.assertTrue(result["auth_blocked"])
        self.assertFalse(result["collection_success"])
        self.assertEqual(1, self.InvoiceDetailWorker.process.call_count)

    def test_mismatched_profile_is_not_collected(self):
        self.ProfileService.fetch_profile.return_value = {"tax_code": "another", "company_name": "Company"}
        result = self.collect()
        self.assertFalse(result["collection_success"])
        self.InvoiceListService.fetch_invoice_identifiers.assert_not_called()

    def test_report_counts_post_login_error_and_escapes_html(self):
        notifier = object.__new__(TelegramNotifier)
        notifier.send_message = MagicMock(return_value=True)
        notifier._format_timestamp = MagicMock(return_value="test")
        notifier.send_collector_result([
            {"tax_code": "tax", "company_name": "A & B", "login_success": True, "collection_success": False, "error": "HTML <error>"},
            {"tax_code": "ok", "login_success": True, "collection_success": True},
        ], 1)
        message = notifier.send_message.call_args.args[0]
        self.assertIn("2 (1 OK, 1 lỗi)", message)
        self.assertIn("A &amp; B (tax): ❌", message)
        self.assertIn("HTML &lt;error&gt;", message)
        self.assertIn("Status: Có lỗi", message)

    def test_legacy_login_flag_does_not_hide_error(self):
        notifier = object.__new__(TelegramNotifier)
        notifier.send_message = MagicMock()
        notifier._format_timestamp = MagicMock(return_value="test")
        notifier.send_collector_result([{"tax_code": "tax", "login_success": True, "error": "failed"}], 1)
        self.assertIn("1 (0 OK, 1 lỗi)", notifier.send_message.call_args.args[0])


class ManualJobAccuracyTests(unittest.TestCase):
    def run_job(self, detail_error):
        from backend.collector import job_manager
        from contextlib import ExitStack
        with ExitStack() as stack:
            mocks = {}
            for target in [
                "backend.database.get_connection", "backend.database.init_database", "backend.database.close_connection",
                "backend.database.repository.InvoiceRepository", "backend.database.item_repository.InvoiceItemRepository",
                "backend.database.company_repository.CompanyRepository", "backend.database.collector_schedule_repository.CollectorScheduleRepository",
                "backend.collector.http.HoaDonHttpClient", "backend.collector.http.LoginService", "backend.collector.http.ProfileService",
                "backend.collector.captcha.SvgCaptchaSolver", "backend.collector.invoice.InvoiceListService",
                "backend.collector.invoice.InvoiceDetailWorker", "backend.collector.job_manager.TelegramNotifier",
                "backend.collector.job_manager.JobManager", "backend.collector.job_manager.time.sleep",
            ]:
                mocks[target.rsplit(".", 1)[1]] = stack.enter_context(patch(target))
            mocks["ProfileService"].return_value.fetch_profile.return_value = {"tax_code": "tax", "company_name": "Company"}
            mocks["InvoiceListService"].return_value.fetch_invoice_identifiers.side_effect = [[SimpleNamespace(id="invoice")], []]
            mocks["InvoiceListService"].return_value.failed_ranges = []
            mocks["InvoiceDetailWorker"].return_value.process.side_effect = detail_error
            mocks["InvoiceDetailWorker"].return_value.process.return_value = True
            job_manager.run_collector_job("job", {"tax_code": "tax", "username": "user", "password": "password"}, date(2026, 10, 21), date(2026, 10, 21))
            return mocks

    def test_partial_detail_failure_is_failed_job_without_success_message(self):
        from backend.collector.job_manager import JobStatus
        mocks = self.run_job(GdtRequestError("detail unavailable"))
        statuses = [call.kwargs.get("status") for call in mocks["JobManager"].return_value.update_job.call_args_list]
        self.assertIn(JobStatus.FAILED, statuses)
        self.assertNotIn(JobStatus.COMPLETED, statuses)
        mocks["TelegramNotifier"].return_value.send_job_completed.assert_not_called()
        mocks["TelegramNotifier"].return_value.send_job_failed.assert_called_once()
        mocks["close_connection"].assert_not_called()

    def test_successful_job_still_completes(self):
        from backend.collector.job_manager import JobStatus
        mocks = self.run_job(None)
        statuses = [call.kwargs.get("status") for call in mocks["JobManager"].return_value.update_job.call_args_list]
        self.assertIn(JobStatus.COMPLETED, statuses)
        self.assertNotIn(JobStatus.FAILED, statuses)
        mocks["TelegramNotifier"].return_value.send_job_completed.assert_called_once()
        mocks["HoaDonHttpClient"].return_value.session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
