import logging

logger = logging.getLogger(__name__)


class ProfileService:
    """
    Handle taxpayer profile data.
    """

    def __init__(self, http_client):
        self.http = http_client

    def fetch_profile(self) -> dict:
        raw = self.http.get_profile()

        tin_info = raw.get("tinInfoTT86") or {}

        tax_code = (
                tin_info.get("mst")
                or raw.get("id")
                or raw.get("username")
        )

        profile = {
            "tax_code": tax_code,
            "company_name": raw.get("name"),
            "authorities": raw.get("authorities", []),
            "raw": raw,
        }

        logger.info(
            "Profile fetched: tax_code=%s, company=%s",
            profile["tax_code"],
            profile["company_name"]
        )

        return profile

