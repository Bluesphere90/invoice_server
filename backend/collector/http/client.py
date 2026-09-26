import requests
import logging
import threading
import time
import uuid
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

    def request(self, method: str, url: str, *, request_profile: str | None = None, **kwargs) -> requests.Response:
        """
        Generic request wrapper with retry logic for 429 and 5xx.
        """
        import time
        import random
        
        max_retries = 5
        base_backoff = 2
        request_kwargs = dict(kwargs)
        extra_headers = request_kwargs.pop("headers", {})
        timeout = request_kwargs.pop("timeout", self.timeout)
        
        for attempt in range(1, max_retries + 1):
            try:
                self._wait_for_request_slot()
                headers = self._headers_for(request_profile)
                headers.update(extra_headers)
                self.last_request_id = headers["Request-Id"]
                self.last_request_profile = request_profile
                resp = self.session.request(method, url, timeout=timeout, headers=headers, **request_kwargs)

                if resp.status_code == 403 and self._is_behavior_block(resp):
                    raise GdtAuthenticationBlockedError(
                        "GDT blocked the request as invalid behavior",
                        request_id=headers["Request-Id"],
                        request_profile=request_profile,
                    )
                
                if resp.status_code == 429:
                    wait_time = base_backoff * (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                    logger.warning(
                        "Rate limited (429) at %s. Attempt %d/%d. Waiting %.2fs...",
                        url, attempt, max_retries, wait_time
                    )
                    time.sleep(wait_time)
                    continue
                
                if resp.status_code >= 500:
                    wait_time = base_backoff + random.uniform(0, 2)
                    logger.warning(
                        "Server error (%d) at %s. Attempt %d/%d. Waiting %.2fs...",
                        resp.status_code, url, attempt, max_retries, wait_time
                    )
                    time.sleep(wait_time)
                    continue
                
                return resp
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                wait_time = base_backoff + random.uniform(0, 2)
                logger.warning(
                    "Network error (%s) at %s. Attempt %d/%d. Waiting %.2fs...",
                    type(e).__name__, url, attempt, max_retries, wait_time
                )
                if attempt == max_retries:
                    raise
                time.sleep(wait_time)
        
        # If we got here, all retries failed (most likely with 429 or 5xx)
        # Just return the last response and let the caller handle it or raise_for_status
        return resp

    @staticmethod
    def _is_behavior_block(resp: requests.Response) -> bool:
        """Identify the GDT 403 response that requires the circuit breaker."""
        try:
            message = str(resp.json().get("message", ""))
        except Exception:
            message = resp.text
        return "hành vi không hợp lệ" in message.lower()

    # ---------- CAPTCHA ----------

    def get_captcha(self) -> dict:
        url = BASE_URL + CAPTCHA_ENDPOINT
        logger.info("GET captcha: %s", url)

        try:
            resp = self.request("GET", url, request_profile="captcha")
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
            )
            
            self._log_response(resp, "POST authenticate")

            # Do NOT raise immediately – API returns 200 even for some failures
            try:
                data = resp.json()
            except Exception:
                logger.error("Auth non-JSON response: %s", resp.text)
                raise RuntimeError(
                    f"Auth failed: non-JSON response ({resp.status_code})"
                )

            if resp.status_code != 200:
                logger.error("Auth HTTP error: %s", resp.status_code)
                raise RuntimeError(
                    f"Auth HTTP error {resp.status_code}"
                )

            if "token" not in data:
                logger.error("Auth response missing token")
                raise RuntimeError(
                    "Auth failed: token missing"
                )

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
            resp = self.request("GET", url, request_profile="lookup")
            self._log_response(resp, "GET profile")

            if resp.status_code != 200:
                logger.error("Profile fetch error: %s (Status: %d)", resp.text, resp.status_code)
                raise RuntimeError(
                    f"Profile HTTP error {resp.status_code}: {resp.text}"
                )

            try:
                data = resp.json()
            except Exception:
                logger.error("Profile non-JSON response")
                raise RuntimeError(f"Profile response is not valid JSON: {resp.text[:500]}")

            return data
        except Exception as e:
            logger.error("Failed to fetch profile: %s", e)
            raise
