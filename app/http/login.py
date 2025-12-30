import logging
from app.http.client import HoaDonHttpClient
from app.captcha.svg_solver import SvgCaptchaSolver

logger = logging.getLogger(__name__)






class LoginService:
    """
    High-level login flow.
    Combines HTTP client + captcha solver.
    """
    captcha_solver = SvgCaptchaSolver()

    def __init__(self, http_client: HoaDonHttpClient, captcha_solver):
        self.http = http_client
        self.captcha_solver = captcha_solver

    def login(self, username: str, password: str) -> str:
        """
        Perform full login flow.
        Returns Bearer token.
        """

        # 1. Fetch captcha
        captcha = self.http.get_captcha()
        svg = captcha["svg"]
        ckey = captcha["key"]

        # 2. Solve captcha
        cvalue = self.captcha_solver.solve(svg)
        if not cvalue:
            raise RuntimeError("Captcha solving failed")

        logger.info("Captcha solved: %s", cvalue)

        # 3. Authenticate
        auth_resp = self.http.authenticate(
            username=username,
            password=password,
            captcha_value=cvalue,
            captcha_key=ckey
        )

        token = auth_resp["token"]
        self.http.set_bearer_token(token)

        logger.info("Login successful")
        return token
