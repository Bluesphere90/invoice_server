import requests
import logging
from .endpoints import BASE_URL, CAPTCHA_ENDPOINT, AUTH_ENDPOINT, PROFILE_ENDPOINT

logger = logging.getLogger(__name__)


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
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        })

    # ---------- CAPTCHA ----------

    def get_captcha(self) -> dict:
        url = BASE_URL + CAPTCHA_ENDPOINT
        logger.debug("GET captcha")

        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()

        data = resp.json()

        if "key" not in data:
            raise ValueError(f"Captcha response missing key: {data}")

        # SVG field name is not consistent
        svg = (
                data.get("svg")
                or data.get("data")
                or data.get("content")
        )

        if not svg:
            raise ValueError(f"Captcha SVG not found in response: {data}")

        return {
            "key": data["key"],
            "svg": svg
        }

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
        logger.debug("POST authenticate")

        resp = self.session.post(
            url,
            json=payload,
            timeout=self.timeout
        )

        # Do NOT raise immediately – API returns 200 even for some failures
        try:
            data = resp.json()
        except Exception:
            raise RuntimeError(
                f"Auth failed: non-JSON response ({resp.status_code})"
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Auth HTTP error {resp.status_code}: {data}"
            )

        if "token" not in data:
            raise RuntimeError(
                f"Auth failed: token missing, response={data}"
            )

        return data

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
        logger.debug("GET profile")

        resp = self.session.get(url, timeout=self.timeout)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Profile HTTP error {resp.status_code}: {resp.text}"
            )

        try:
            data = resp.json()
        except Exception:
            raise RuntimeError("Profile response is not valid JSON")

        return data