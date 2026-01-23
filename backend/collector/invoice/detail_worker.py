import logging
import time
from typing import Dict, Any

from backend.collector.invoice.detail_endpoints import build_invoice_detail_url
from backend.observability.logger import get_logger

logger = get_logger(__name__)


class InvoiceDetailWorker:
    """
    FULL invoice detail downloader.
    Ported from:
      - GetInvoiceDetailsAsync (C#)
      - Retry + DetailStatus logic
    """

    MAX_RETRIES = 10

    def __init__(self, http_client, invoice_repo, item_repo):
        """
        http_client : HoaDonHttpClient
        invoice_repo: InvoiceRepository
        item_repo   : InvoiceItemRepository
        """
        self.http = http_client
        self.invoice_repo = invoice_repo
        self.item_repo = item_repo

    # =====================================================
    # PUBLIC
    # =====================================================

    def process(self, identifier):
        invoice_id = identifier.id

        if not self.invoice_repo.should_retry_detail(invoice_id):
            logger.info("Skip invoice %s (no retry)", invoice_id)
            return

        url = build_invoice_detail_url(identifier)

        retry = 0
        while retry <= self.MAX_RETRIES:
            try:
                logger.info("Fetch detail %s (try %s)", invoice_id, retry)

                resp = self.http.session.get(url, timeout=30)

                # -------- SUCCESS --------
                if resp.status_code == 200:
                    data = resp.json()
                    self._save_invoice_detail(invoice_id, data)
                    self.invoice_repo.update_detail_status(
                        invoice_id, status=1
                    )
                    logger.info("Detail OK %s", invoice_id)
                    # Rate limit protection: wait 1.5s between requests
                    # Based on testing: 0s=77% (conn errors), 1s=60%, 1.5s=87%
                    time.sleep(1.5)
                    return

                # -------- RATE LIMIT --------
                if resp.status_code == 429:
                    retry += 1
                    self._backoff(retry)
                    continue

                # -------- OTHER HTTP ERROR --------
                logger.error(
                    "Detail HTTP error %s %s",
                    resp.status_code,
                    invoice_id,
                )
                self._fail(invoice_id)
                return

            except Exception as exc:
                logger.exception(
                    "Exception fetching detail %s: %s",
                    invoice_id,
                    exc,
                )
                retry += 1
                if retry > self.MAX_RETRIES:
                    self._fail(invoice_id)
                    return
                self._backoff(retry)

    # =====================================================
    # INTERNAL
    # =====================================================

    def _save_invoice_detail(self, invoice_id: str, data: Dict[str, Any]):
        """
        Save full header + items.
        """

        # 1️⃣ Update invoice header (FULL JSON)
        header = dict(data)
        header["id"] = invoice_id

        self.invoice_repo.upsert_invoice_summary(header)

        # 2️⃣ Items
        items = data.get("hdhhdvu") or []
        if not items:
            logger.warning("No items for invoice %s", invoice_id)
            return

        for item in items:
            item["idhdon"] = invoice_id
            self.item_repo.upsert_item(item)

    def _fail(self, invoice_id: str):
        self.invoice_repo.update_detail_status(
            invoice_id,
            status=-1,
            increment_retry=True,
        )
        logger.error("Detail FAILED %s", invoice_id)

    @staticmethod
    def _backoff(retry: int):
        """
        Exponential backoff (nhẹ).
        """
        sleep_sec = min(2 ** retry, 60)
        time.sleep(sleep_sec)
