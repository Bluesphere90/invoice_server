import logging
import time
from typing import Dict, Any

from app.invoice.detail_endpoints import build_invoice_detail_url

logger = logging.getLogger(__name__)


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
            item["tthue"] = self._resolve_tthue(item)
            self.item_repo.upsert_item(item)

    @staticmethod
    def _resolve_tthue(item: dict) -> "str | None":
        """
        Layered tthue resolution:
          1. Native tthue field
          2. Named field in ttkhac array
          3. Amount - thtien from ttkhac
          4. thtien * tsuat
          5. Exempt label -> 0
          6. None
        """
        existing = item.get("tthue")
        if existing is not None and str(existing).strip() != "":
            return str(existing)

        thtien = item.get("thtien")
        tsuat  = item.get("tsuat")
        ltsuat = (item.get("ltsuat") or "").strip().upper()
        ttkhac = item.get("ttkhac")

        if isinstance(ttkhac, list):
            TAX_FIELD_NAMES = {
                "VATAmount",
                "Ti\u1ec1n thu\u1ebf",
                "Ti\u1ec1n thu\u1ebf d\u00f2ng (Ti\u1ec1n thu\u1ebf GTGT)",
                "Ti\u1ec1n thu\u1ebf s\u1ea3n ph\u1ea9m",
                "TThue",
            }
            amount_val = None
            for field in ttkhac:
                if not isinstance(field, dict):
                    continue
                ttruong = field.get("ttruong", "")
                dlieu   = field.get("dlieu")
                if ttruong in TAX_FIELD_NAMES and dlieu is not None and str(dlieu).strip() != "":
                    return str(dlieu)
                if ttruong == "Amount" and dlieu is not None:
                    try:
                        amount_val = float(dlieu)
                    except (ValueError, TypeError):
                        pass
            if amount_val is not None and thtien is not None:
                try:
                    derived = round(amount_val - float(thtien))
                    if derived >= 0:
                        return str(derived)
                except (ValueError, TypeError):
                    pass

        if thtien is not None and tsuat is not None:
            try:
                if float(tsuat) > 0:
                    return str(round(float(thtien) * float(tsuat)))
            except (ValueError, TypeError):
                pass

        EXEMPT_LABELS = {"KKKNT", "KCT", "KHAC", "0%"}
        if ltsuat in EXEMPT_LABELS or (tsuat is not None and float(tsuat) == 0):
            return "0"

        return None


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
