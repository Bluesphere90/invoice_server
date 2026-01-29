import requests
import json
import logging
from .endpoints import BASE_URL, CAPTCHA_ENDPOINT, AUTH_ENDPOINT, PROFILE_ENDPOINT
from backend.observability.logger import get_logger

logger = get_logger(__name__)


class HoaDonHttpClient:
    """
    Low-level HTTP client.
    Responsible ONLY for HTTP communication.
    No business logic here.
    """

    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.timeout = timeout

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        })

    def _log_response(self, resp, context: str):
        """Helper to log response details."""
        try:
            logger.info(
                "%s: %s %s completed in %.2fs. Status: %d", 
                context, resp.request.method, resp.url, resp.elapsed.total_seconds(), resp.status_code
            )
            
            if resp.status_code >= 400:
                logger.error(
                    "%s FAILED: %s. Response: %s", 
                    context, resp.status_code, resp.text[:1000]
                )
        except Exception:
            pass

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Generic request wrapper with retry logic for 429 and 5xx.
        """
        import time
        import random
        
        max_retries = 5
        base_backoff = 2
        
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                
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

    # ---------- CAPTCHA ----------

    def get_captcha(self) -> dict:
        url = BASE_URL + CAPTCHA_ENDPOINT
        logger.info("GET captcha: %s", url)

        try:
            resp = self._request("GET", url)
            self._log_response(resp, "GET captcha")
            resp.raise_for_status()

            data = resp.json()

            if "key" not in data:
                logger.error("Captcha missing key: %s", data)
                raise ValueError(f"Captcha response missing key: {data}")

            # SVG field name is not consistent
            svg = (
                    data.get("svg")
                    or data.get("data")
                    or data.get("content")
            )

            if not svg:
                logger.error("Captcha SVG not found: %s", data)
                raise ValueError(f"Captcha SVG not found in response: {data}")

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
            resp = self._request(
                "POST",
                url,
                json=payload
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
                logger.error("Auth HTTP error: %s", data)
                raise RuntimeError(
                    f"Auth HTTP error {resp.status_code}: {data}"
                )

            if "token" not in data:
                logger.error("Auth missing token: %s", data)
                raise RuntimeError(
                    f"Auth failed: token missing, response={data}"
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
            resp = self._request("GET", url)
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