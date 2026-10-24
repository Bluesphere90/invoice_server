import requests
import logging
import threading
import time
import uuid
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from .endpoints import BASE_URL, CAPTCHA_ENDPOINT, AUTH_ENDPOINT, PROFILE_ENDPOINT
from backend.config import settings
from backend.observability.logger import get_logger

logger = get_logger(__name__)


class GdtAuthenticationBlockedError(RuntimeError):
    """GDT rejected authentication as invalid automated behavior."""

    def __init__(self, message: str, request_id: str, request_profile: str | None):
        self.request_id = request_id
        self.request_profile = request_profile or "default"
        super().__init__(
            f"{message} (request_id={request_id}, profile={self.request_profile})"
        )


class GdtRequestError(RuntimeError):
    """An incomplete GDT request; safe metadata only, never response bodies."""


class GdtInvalidResponseError(GdtRequestError):
    """The gateway returned HTML, empty content, or an invalid API envelope."""


class HoaDonHttpClient:
    """
    Low-level HTTP client.
    Responsible ONLY for HTTP communication.
    No business logic here.
    """

    _request_gate_lock = threading.Lock()
    _last_request_at = 0.0

    _PROFILE_HEADERS = {
        "captcha": {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://hoadondientu.gdt.gov.vn/",
        },
        "login": {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://hoadondientu.gdt.gov.vn/",
            "Origin": "https://hoadondientu.gdt.gov.vn",
        },
        "lookup": {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don",
        },
        "detail": {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://hoadondientu.gdt.gov.vn/tra-cuu/tra-cuu-hoa-don",
        },
    }

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.timeout = timeout
        self.last_request_id: str | None = None
        self.last_request_profile: str | None = None

        self.session.headers.update({
            "User-Agent": settings.HDDT_BROWSER_USER_AGENT,
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua": '"Chromium";v="126", "Microsoft Edge";v="126", "Not.A/Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        })

    @classmethod
    def _wait_for_request_slot(cls):
        """Apply one process-wide delay across all GDT requests."""
        with cls._request_gate_lock:
            now = time.monotonic()
            delay_seconds = settings.HDDT_REQUEST_DELAY_MS / 1000
            remaining = delay_seconds - (now - cls._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
            cls._last_request_at = time.monotonic()

    def _headers_for(self, request_profile: str | None) -> dict:
        headers = dict(self._PROFILE_HEADERS.get(request_profile or "", {}))
        headers["Request-Id"] = str(uuid.uuid4())
        return headers

    def _log_response(self, resp, context: str):
        """Log request metadata only; responses may contain sensitive data."""
        try:
            logger.info(
                "%s: %s %s completed in %.2fs. Status: %d", 
                context, resp.request.method, resp.url, resp.elapsed.total_seconds(), resp.status_code
            )
            
            if resp.status_code >= 400:
                logger.error(
                    "%s FAILED with HTTP status %s",
                    context, resp.status_code,
                )
        except Exception:
            pass

    MAX_REQUEST_ATTEMPTS = 5
    MAX_RETRY_WAIT_SECONDS = 60

    @staticmethod
    def _response_metadata(resp):
        content_type = resp.headers.get("Content-Type", "unknown").split(";", 1)[0]
        return f"HTTP {resp.status_code}, content-type={content_type}, bytes={len(resp.content)}"

    def _validate_json_response(self, resp, response_kind):
        try:
            data = resp.json()
        except ValueError:
            body = resp.text.lstrip().lower()
            kind = "empty" if not body else "HTML" if body.startswith("<") else "non-JSON"
            raise GdtInvalidResponseError(
                f"{kind} response ({self._response_metadata(resp)})"
            ) from None
        if not isinstance(data, dict):
            raise GdtInvalidResponseError("API response is not a JSON object")
        if response_kind == "list":
            if not isinstance(data.get("datas"), list):
                raise GdtInvalidResponseError("Invoice list response missing a valid datas array")
            if data.get("state") is not None and not isinstance(data["state"], str):
                raise GdtInvalidResponseError("Invoice list response has an invalid pagination state")
        if response_kind == "captcha":
            svg = data.get("svg") or data.get("data") or data.get("content")
            if not data.get("key") or not isinstance(svg, str) or not svg:
                raise GdtInvalidResponseError("Captcha response missing key or SVG")
        if response_kind == "profile":
            info = data.get("tinInfoTT86")
            if not ((isinstance(info, dict) and info.get("mst")) or data.get("id") or data.get("username")):
                raise GdtInvalidResponseError("Profile response missing taxpayer identifier")
        if response_kind == "detail":
            if not data.get("id") or not isinstance(data.get("hdhhdvu"), list):
                raise GdtInvalidResponseError("Invoice detail response missing id or items")
        return data

    @classmethod
    def _retry_delay(cls, attempt, response):
        delay = min(5 * (2 ** (attempt - 1)) + random.uniform(0, 1), cls.MAX_RETRY_WAIT_SECONDS)
        value = response.headers.get("Retry-After") if response is not None else None
        if value:
            try:
                retry_after = float(value)
            except (ValueError, TypeError):
                try:
                    retry_after = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    retry_after = 0
            if retry_after > cls.MAX_RETRY_WAIT_SECONDS:
                raise GdtRequestError("GDT requested a longer Retry-After; retry on a later collector run")
            delay = max(delay, retry_after)
        return delay

    def request(self, method: str, url: str, *, request_profile: str | None = None,
                response_kind: str | None = None, max_attempts: int | None = None,
                **kwargs) -> requests.Response:
        """The only retry layer: bounded retries for transport, 429/5xx and invalid JSON."""
        attempts = self.MAX_REQUEST_ATTEMPTS if max_attempts is None else max_attempts
        if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= self.MAX_REQUEST_ATTEMPTS:
            raise ValueError("max_attempts must be between 1 and MAX_REQUEST_ATTEMPTS")
        request_kwargs = dict(kwargs)
        extra_headers = request_kwargs.pop("headers", {})
        timeout = request_kwargs.pop("timeout", self.timeout)
        endpoint = urlsplit(url).path
        context = f"GDT {request_profile or 'request'} {endpoint}"

        for attempt in range(1, attempts + 1):
            resp = None
            self._wait_for_request_slot()
            headers = self._headers_for(request_profile)
            headers.update(extra_headers)
            self.last_request_id = headers["Request-Id"]
            self.last_request_profile = request_profile
            try:
                resp = self.session.request(method, url, timeout=timeout, headers=headers, **request_kwargs)
                self._log_response(resp, context)
                if resp.status_code == 403 and self._is_behavior_block(resp):
                    raise GdtAuthenticationBlockedError(
                        "GDT blocked the request as invalid behavior",
                        request_id=self.last_request_id, request_profile=request_profile,
                    )
                if resp.status_code == 429 or resp.status_code >= 500:
                    reason = self._response_metadata(resp)
                else:
                    if resp.status_code >= 400:
                        raise GdtRequestError(
                            f"{context}: {self._response_metadata(resp)}; request_id={self.last_request_id}"
                        )
                    if response_kind:
                        self._validate_json_response(resp, response_kind)
                    return resp
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                reason = type(exc).__name__
            except GdtInvalidResponseError as exc:
                reason = str(exc)

            if resp is not None:
                resp.close()
            if attempt == attempts:
                raise GdtRequestError(
                    f"{context} failed after {attempt} attempts: {reason}; request_id={self.last_request_id}"
                ) from None
            delay = self._retry_delay(attempt, resp)
            logger.warning("%s: %s; attempt %d/%d, retry in %.1fs; request_id=%s",
                           context, reason, attempt, attempts, delay, self.last_request_id)
            time.sleep(delay)

    @staticmethod
    def _is_behavior_block(resp: requests.Response) -> bool:
        """Identify the GDT 403 response that requires the circuit breaker."""
        try:
            data = resp.json()
            message = str(data.get("message", "")) if isinstance(data, dict) else resp.text
        except Exception:
            message = resp.text
        return "hành vi không hợp lệ" in message.lower()

    # ---------- CAPTCHA ----------

    def get_captcha(self) -> dict:
        url = BASE_URL + CAPTCHA_ENDPOINT
        logger.info("GET captcha: %s", url)

        try:
            resp = self.request("GET", url, request_profile="captcha", response_kind="captcha")
            self._log_response(resp, "GET captcha")
            resp.raise_for_status()

            data = resp.json()

            if "key" not in data:
                logger.error("Captcha response missing key")
                raise ValueError("Captcha response missing key")

            # SVG field name is not consistent
            svg = (
                    data.get("svg")
                    or data.get("data")
                    or data.get("content")
            )

            if not svg:
                logger.error("Captcha SVG not found")
                raise ValueError("Captcha SVG not found in response")

            return {
                "key": data["key"],
                "svg": svg
            }
        except Exception as e:
            logger.error("Failed to get captcha: %s", e)
            raise

    # ---------- AUTH ----------

    def authenticate(
        self,
        username: str,
        password: str,
        captcha_value: str,
        captcha_key: str
    ) -> dict:
        """
        Perform login.
        Returns response JSON (contains token if success).
        """

        payload = {
            "username": username,
            "password": password,
            "cvalue": captcha_value,
            "ckey": captcha_key
        }

        url = BASE_URL + AUTH_ENDPOINT
        logger.info("POST authenticate: %s", url)

        try:
            resp = self.request(
                "POST",
                url,
                json=payload,
                request_profile="login",
                response_kind="auth",
            )
            
            self._log_response(resp, "POST authenticate")

            data = resp.json()
            if not isinstance(data.get("token"), str) or not data["token"]:
                raise GdtRequestError("GDT login: token missing; check credentials or captcha")

            return data
        except Exception as e:
            logger.error("Authentication failed: %s", e)
            raise

    # ---------- AUTH HEADER ----------

    def set_bearer_token(self, token: str):
        """
        Set Authorization header for subsequent requests.
        """
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })

    # ---------- PROFILE ----------

    def get_profile(self) -> dict:
        """
        Fetch authenticated taxpayer profile.
        Requires Authorization header to be set.
        """
        url = BASE_URL + PROFILE_ENDPOINT
        logger.info("GET profile: %s", url)

        try:
            resp = self.request("GET", url, request_profile="lookup", response_kind="profile")
            data = resp.json()
            return data
        except Exception as e:
            logger.error("Failed to fetch profile: %s", e)
            raise
