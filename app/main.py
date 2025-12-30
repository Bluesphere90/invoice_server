import logging
from app.http.client import HoaDonHttpClient
from app.http.login import LoginService
from app.http.profile import ProfileService
from app.captcha.svg_solver import SvgCaptchaSolver

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

USERNAME = "0202180901"
PASSWORD = "123456aA@"


def main():
    http_client = HoaDonHttpClient()
    captcha_solver = SvgCaptchaSolver()

    login_service = LoginService(http_client, captcha_solver)
    token = login_service.login(USERNAME, PASSWORD)

    print("TOKEN OK")

    profile_service = ProfileService(http_client)
    profile = profile_service.fetch_profile()

    print("PROFILE:")
    for k, v in profile.items():
        print(f"  {k}: {v}")



if __name__ == "__main__":
    main()
