import unittest
from uuid import UUID
from unittest.mock import MagicMock, patch

from backend.collector.http.client import (
    GdtAuthenticationBlockedError,
    HoaDonHttpClient,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {}
        self.text = str(self._payload)
        self.elapsed = MagicMock()
        self.elapsed.total_seconds.return_value = 0.01
        self.request = MagicMock(method="GET", url="https://example.test")

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class HttpProtocolTests(unittest.TestCase):
    def setUp(self):
        HoaDonHttpClient._last_request_at = 0.0
        self.client = HoaDonHttpClient()
        self.client._log_response = MagicMock()
        self.client.session.request = MagicMock(return_value=FakeResponse())

    def test_login_profile_adds_request_id_and_origin(self):
        self.client.request("POST", "https://example.test/login", request_profile="login")
        headers = self.client.session.request.call_args.kwargs["headers"]
        UUID(headers["Request-Id"])
        self.assertEqual("https://hoadondientu.gdt.gov.vn", headers["Origin"])
        self.assertEqual("https://hoadondientu.gdt.gov.vn/", headers["Referer"])

    def test_authorization_is_added_only_after_login(self):
        self.client.request("GET", "https://example.test/profile", request_profile="lookup")
        self.assertNotIn("Authorization", self.client.session.headers)
        self.client.set_bearer_token("token-value")
        self.client.request("GET", "https://example.test/profile", request_profile="lookup")
        self.assertEqual("Bearer token-value", self.client.session.headers["Authorization"])

    def test_captcha_profile_has_no_origin_or_content_type(self):
        self.client.request("GET", "https://example.test/captcha", request_profile="captcha")
        headers = self.client.session.request.call_args.kwargs["headers"]
        self.assertNotIn("Origin", headers)
        self.assertNotIn("Content-Type", headers)
        self.assertEqual("https://hoadondientu.gdt.gov.vn/", headers["Referer"])

    def test_lookup_and_detail_profiles_use_lookup_referer(self):
        self.client.request("GET", "https://example.test/lookup", request_profile="lookup")
        lookup_headers = self.client.session.request.call_args.kwargs["headers"]
        self.client.request("GET", "https://example.test/detail", request_profile="detail")
        detail_headers = self.client.session.request.call_args.kwargs["headers"]

        expected_referer = "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don"
        self.assertEqual(expected_referer, lookup_headers["Referer"])
        self.assertEqual(expected_referer, detail_headers["Referer"])
        self.assertNotIn("Origin", lookup_headers)
        self.assertNotIn("Origin", detail_headers)
        self.assertNotEqual(lookup_headers["Request-Id"], detail_headers["Request-Id"])

    @patch("backend.collector.http.client.time.sleep")
    def test_retry_uses_a_new_request_id(self, _sleep):
        self.client.session.request.side_effect = [FakeResponse(429), FakeResponse(200)]
        self.client.request("GET", "https://example.test", request_profile="lookup")
        first = self.client.session.request.call_args_list[0].kwargs["headers"]["Request-Id"]
        second = self.client.session.request.call_args_list[1].kwargs["headers"]["Request-Id"]
        self.assertNotEqual(first, second)

    @patch("backend.collector.http.client.time.sleep")
    def test_5xx_retries(self, _sleep):
        self.client.session.request.side_effect = [FakeResponse(503), FakeResponse(200)]
        response = self.client.request("GET", "https://example.test", request_profile="lookup")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, self.client.session.request.call_count)

    def test_behavior_block_is_classified(self):
        self.client.session.request.return_value = FakeResponse(
            403, {"message": "Hệ thống phát hiện hành vi không hợp lệ."}
        )
        with self.assertRaises(GdtAuthenticationBlockedError) as caught:
            self.client.authenticate("user", "password", "captcha", "key")
        self.assertEqual(1, self.client.session.request.call_count)
        UUID(caught.exception.request_id)
        self.assertEqual("login", caught.exception.request_profile)

    def test_list_and_detail_do_not_bypass_gateway(self):
        from backend.collector.invoice.detail_worker import InvoiceDetailWorker
        from backend.collector.invoice.list_service import InvoiceListService
        import inspect

        self.assertNotIn("session.get(", inspect.getsource(InvoiceListService))
        self.assertNotIn("session.get(", inspect.getsource(InvoiceDetailWorker))

    def test_list_records_valid_gateway_responses(self):
        from backend.collector.invoice.list_service import InvoiceListService

        gateway = MagicMock()
        gateway.request.return_value = FakeResponse(200, {"datas": []})
        service = InvoiceListService(gateway, MagicMock())

        self.assertEqual({"datas": []}, service._fetch_with_retry("https://example.test/list"))
        self.assertEqual(1, service.successful_response_count)


class CircuitBreakerTests(unittest.TestCase):
    @patch("backend.collector.main.close_connection")
    @patch("backend.collector.main.HealthRecorder")
    @patch("backend.collector.main.TelegramNotifier")
    @patch("backend.collector.main.collect_for_company")
    @patch("backend.collector.main.CollectorScheduleRepository")
    @patch("backend.collector.main.CompanyRepository")
    @patch("backend.collector.main.InvoiceItemRepository")
    @patch("backend.collector.main.InvoiceRepository")
    @patch("backend.collector.main.get_connection")
    @patch("backend.collector.main.init_database")
    def test_behavior_block_stops_remaining_companies(
        self,
        _init_database,
        _get_connection,
        _invoice_repo,
        _item_repo,
        company_repository,
        schedule_repository,
        collect_for_company,
        _notifier,
        _health,
        _close_connection,
    ):
        company_repository.return_value.get_active_companies.return_value = [
            {"tax_code": "first"}, {"tax_code": "second"}
        ]
        schedule_repository.return_value.is_active.return_value = True
        collect_for_company.return_value = {
            "auth_blocked": True,
            "error": "blocked",
            "login_success": False,
            "invoices_detected": 0,
            "invoices_downloaded": 0,
            "download_failed": 0,
        }

        from backend.collector.main import run_collector

        run_collector()

        self.assertEqual(1, collect_for_company.call_count)
        schedule_repository.return_value.disable_for_auth_block.assert_called_once()

    @patch("backend.collector.main.close_connection")
    @patch("backend.collector.main.HealthRecorder")
    @patch("backend.collector.main.TelegramNotifier")
    @patch("backend.collector.main.collect_for_company")
    @patch("backend.collector.main.CollectorScheduleRepository")
    @patch("backend.collector.main.CompanyRepository")
    @patch("backend.collector.main.InvoiceItemRepository")
    @patch("backend.collector.main.InvoiceRepository")
    @patch("backend.collector.main.get_connection")
    @patch("backend.collector.main.init_database")
    def test_disabled_schedule_makes_no_outbound_request(
        self,
        _init_database,
        _get_connection,
        _invoice_repo,
        _item_repo,
        _company_repository,
        schedule_repository,
        collect_for_company,
        _notifier,
        _health,
        _close_connection,
    ):
        schedule_repository.return_value.is_active.return_value = False
        from backend.collector.main import run_collector

        run_collector()

        collect_for_company.assert_not_called()


if __name__ == "__main__":
    unittest.main()
