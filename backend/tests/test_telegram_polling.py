"""Telegram polling regressions: all HTTP requests and message handlers are mocked."""
import asyncio
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

candidate = os.getenv("INVOICE_TEST_BOT_SERVICE_PATH")
if candidate:
    spec = importlib.util.spec_from_file_location("telegram_retry_candidate", candidate)
    bot_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bot_module)
else:
    import backend.telegram.bot_service as bot_module


class PollingRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.log_patch = patch.object(bot_module, "logger", self.logger)
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)
        with patch.object(bot_module, "settings", SimpleNamespace(
            TELEGRAM_BOT_TOKEN="unit-test-token", TELEGRAM_CHAT_ID="unit-test-chat"
        )):
            self.bot = bot_module.TelegramBotService()
        self.bot.handle_update = AsyncMock()
        self.delays = []

    def stop_after_waits(self, count):
        async def wait(delay):
            self.delays.append(delay)
            if len(self.delays) >= count:
                self.bot.stop()
        self.bot._wait_for_poll_retry = AsyncMock(side_effect=wait)

    async def test_network_failure_has_bounded_backoff_and_one_log(self):
        self.bot._request = AsyncMock(side_effect=[{"ok": True}] + [None] * 6)
        self.stop_after_waits(6)
        await self.bot.start_polling()
        self.assertEqual([5, 10, 20, 40, 60, 60], self.delays)
        self.assertEqual(7, self.bot._request.await_count)
        self.assertEqual(1, self.logger.warning.call_count)
        self.assertFalse(self.bot.running)
        for call in self.bot._request.await_args_list:
            self.assertFalse(call.kwargs["log_errors"])

    async def test_empty_success_resets_backoff(self):
        self.bot._request = AsyncMock(side_effect=[
            {"ok": True}, None, None, {"ok": True, "result": []}, None,
        ])
        self.stop_after_waits(3)
        await self.bot.start_polling()
        self.assertEqual([5, 10, 5], self.delays)
        self.assertEqual(2, self.logger.warning.call_count)
        self.assertTrue(any("recovered" in str(c) for c in self.logger.info.call_args_list))

    async def test_api_failure_is_delayed(self):
        self.bot._request = AsyncMock(side_effect=[
            {"ok": True}, {"ok": False, "error_code": 500},
            {"ok": False, "error_code": 401},
        ])
        self.stop_after_waits(2)
        await self.bot.start_polling()
        self.assertEqual([5, 10], self.delays)

    async def test_offline_start_retries_webhook_and_preserves_updates(self):
        self.bot._request = AsyncMock(side_effect=[
            None, {"ok": False}, {"ok": True}, None,
        ])
        self.stop_after_waits(3)
        await self.bot.start_polling()
        self.assertEqual([5, 10, 5], self.delays)
        calls = self.bot._request.await_args_list
        self.assertEqual(["deleteWebhook"] * 3 + ["getUpdates"], [c.args[1] for c in calls])
        for call in calls[:3]:
            self.assertEqual({"drop_pending_updates": False}, call.kwargs["json"])

    async def test_unexpected_exception_is_delayed_without_leaking_text(self):
        self.bot._request = AsyncMock(side_effect=[
            {"ok": True}, ValueError("sensitive-test-marker"),
        ])
        self.stop_after_waits(1)
        await self.bot.start_polling()
        self.assertEqual([5], self.delays)
        self.assertNotIn("sensitive-test-marker", str(self.logger.mock_calls))
        self.assertIn("ValueError", str(self.logger.warning.call_args))

    async def test_server_retry_after_can_exceed_normal_cap(self):
        self.bot._request = AsyncMock(side_effect=[
            {"ok": True}, {"ok": False, "parameters": {"retry_after": 120}},
        ])
        self.stop_after_waits(1)
        await self.bot.start_polling()
        self.assertEqual([120], self.delays)

    async def test_invalid_retry_after_does_not_remove_backoff(self):
        self.bot._request = AsyncMock(side_effect=[{"ok": True}] + [
            {"ok": False, "parameters": {"retry_after": value}}
            for value in [None, -5, "soon", True]
        ])
        self.stop_after_waits(4)
        await self.bot.start_polling()
        self.assertEqual([5, 10, 20, 40], self.delays)

    async def test_update_processing_keeps_offset_and_handler(self):
        update = {"update_id": 26, "message": {"text": "/stats"}}
        self.bot._request = AsyncMock(side_effect=[
            {"ok": True}, {"ok": True, "result": [update]},
        ])
        self.bot.handle_update.side_effect = lambda _update: self.bot.stop()
        await self.bot.start_polling()
        self.assertEqual(27, self.bot.offset)
        self.bot.handle_update.assert_awaited_once_with(update)
        self.assertEqual(0, len(self.delays))

    async def test_stop_interrupts_retry_wait(self):
        self.bot._request = AsyncMock(side_effect=[{"ok": True}, None])
        waiting = asyncio.Event()
        original_wait = self.bot._wait_for_poll_retry
        async def wait(delay):
            waiting.set()
            await original_wait(delay)
        self.bot._wait_for_poll_retry = wait
        task = asyncio.create_task(self.bot.start_polling())
        try:
            await asyncio.wait_for(waiting.wait(), timeout=1)
            self.assertFalse(task.done())
            self.bot.stop()
            await asyncio.wait_for(task, timeout=0.5)
            self.assertEqual(2, self.bot._request.await_count)
            self.assertFalse(self.bot.running)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_task_cancellation_cleans_up_retry(self):
        self.bot._request = AsyncMock(side_effect=[{"ok": True}, None])
        waiting = asyncio.Event()
        original_wait = self.bot._wait_for_poll_retry
        async def wait(delay):
            waiting.set()
            await original_wait(delay)
        self.bot._wait_for_poll_retry = wait
        task = asyncio.create_task(self.bot.start_polling())
        try:
            await asyncio.wait_for(waiting.wait(), timeout=1)
            task.cancel()
            await asyncio.wait_for(task, timeout=0.5)
            self.assertFalse(self.bot.running)
            self.assertTrue(self.bot._polling_stop.is_set())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_stop_during_webhook_does_not_start_get_updates(self):
        async def request(*args, **kwargs):
            self.bot.stop()
            return {"ok": True}
        self.bot._request = AsyncMock(side_effect=request)
        await self.bot.start_polling()
        self.assertEqual(1, self.bot._request.await_count)
        self.bot.handle_update.assert_not_awaited()

    async def test_failure_yields_before_the_next_request(self):
        polling_calls = 0
        async def request(method, endpoint, **kwargs):
            nonlocal polling_calls
            if endpoint == "deleteWebhook":
                return {"ok": True}
            polling_calls += 1
            if polling_calls == 2:
                self.bot.stop()
            return None
        self.bot._request = AsyncMock(side_effect=request)
        async def wait(delay):
            self.delays.append(delay)
        self.bot._wait_for_poll_retry = AsyncMock(side_effect=wait)
        await self.bot.start_polling()
        self.assertEqual([5], self.delays)

    def fake_http_client(self, response=None, error=None):
        client = MagicMock()
        client.post = AsyncMock(return_value=httpx.Response(200, json={"ok": True}))
        client.get = AsyncMock(return_value=response, side_effect=error)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        return client, patch.object(bot_module.httpx, "AsyncClient", return_value=context)

    async def test_real_request_connect_error_cannot_busy_loop(self):
        client, client_patch = self.fake_http_client(
            error=httpx.ConnectError("sensitive-test-marker")
        )
        self.stop_after_waits(6)
        with client_patch:
            await self.bot.start_polling()
        self.assertEqual([5, 10, 20, 40, 60, 60], self.delays)
        self.assertEqual(6, client.get.await_count)
        self.logger.error.assert_not_called()
        self.assertEqual(1, self.logger.warning.call_count)
        self.assertNotIn("sensitive-test-marker", str(self.logger.mock_calls))

    async def test_real_http_429_preserves_retry_after(self):
        response = httpx.Response(429, json={
            "ok": False, "parameters": {"retry_after": 120},
        })
        _, client_patch = self.fake_http_client(response=response)
        self.stop_after_waits(1)
        with client_patch:
            await self.bot.start_polling()
        self.assertEqual([120], self.delays)

    async def test_non_polling_http_error_keeps_existing_contract(self):
        client, client_patch = self.fake_http_client()
        client.post.return_value = httpx.Response(500, json={"ok": False})
        with client_patch:
            result = await self.bot._request("POST", "sendMessage", json={"text": "test"})
        self.assertIsNone(result)
        self.logger.warning.assert_called_once()

    async def test_non_json_api_error_is_delayed(self):
        _, client_patch = self.fake_http_client(
            response=httpx.Response(503, text="upstream unavailable")
        )
        self.stop_after_waits(1)
        with client_patch:
            await self.bot.start_polling()
        self.assertEqual([5], self.delays)


if __name__ == "__main__":
    unittest.main()
