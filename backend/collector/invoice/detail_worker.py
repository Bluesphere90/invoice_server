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

    def process(self, identifier) -> bool:
        invoice_id = identifier.id

        if not self.invoice_repo.should_retry_detail(invoice_id):
            logger.info("Skip invoice %s (no retry)", invoice_id)
            return False

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
                    return True

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
                raise Exception(f"HTTP {resp.status_code} error fetching detail")

            except Exception as exc:
                logger.exception(
                    "Exception fetching detail %s: %s",
                    invoice_id,
                    exc,
                )
                retry += 1
                if retry > self.MAX_RETRIES:
                    self._fail(invoice_id)
                    raise exc
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
        
        # --- FIX: Extract CCCD/CMND to nmmst if nmmst is missing/empty ---
        if not header.get("nmmst"):
            nmttkhac = header.get("nmttkhac")
            if isinstance(nmttkhac, list):
                for item in nmttkhac:
                    if isinstance(item, dict) and item.get("ttruong") == "AccountObjectIdentificationNumber":
                        header["nmmst"] = str(item.get("dlieu"))
                        break

        self.invoice_repo.upsert_invoice_summary(header)

        # 2️⃣ Items
        items = data.get("hdhhdvu") or []
        if not items:
            logger.warning("No items for invoice %s", invoice_id)
            return

        khmshdon = data.get("khmshdon")  # invoice type from header
        for item in items:
            item["idhdon"] = invoice_id
            item["tthue"] = self._resolve_tthue(item, khmshdon=khmshdon)
            self.item_repo.upsert_item(item)

    @staticmethod
    def _resolve_tthue(item: dict, khmshdon: int | None = None) -> str | None:
        """
        Resolve the tthue (tax amount) for a single invoice item using a layered strategy:

        Priority order:
          1. Use the native tthue field if already present.
          2. Search known tax field names inside the ttkhac (additional info) array.
          3. Derive from ttkhac's 'Amount' field: tthue = Amount - thtien
             (Amount is often the with-tax total stored by providers like Grab/Novotel).
          4. Calculate: tthue = round(thtien * tsuat)
             Validated against real data: 99.9% accuracy.
          5. For tax-exempt items (KKKNT, KCT, 0%, tsuat=0): set tthue = '0'.
          6. khmshdon = 2 (Hoa don ban hang) has NO VAT -> tthue = '0'.
          7. Fall back to None if no information is available.
        """
        # ── 1. Native field ──────────────────────────────────────────────────
        existing = item.get("tthue")
        if existing is not None and str(existing).strip() != "":
            return str(existing)

        thtien = item.get("thtien")  # pre-tax line amount (numeric)
        tsuat  = item.get("tsuat")   # tax rate as decimal, e.g. 0.1 for 10%
        ltsuat = (item.get("ltsuat") or "").strip().upper()
        ttkhac = item.get("ttkhac")

        if isinstance(ttkhac, list):
            # ── 2. Known tax field names inside ttkhac ───────────────────────
            TAX_FIELD_NAMES = [
                "VATAmount",
                "Tiền thuế",
                "Tiền thuế dòng (Tiền thuế GTGT)",
                "Tiền thuế sản phẩm",
                "TThue",
            ]
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

            # ── 3. Derive from Amount - thtien ───────────────────────────────
            if amount_val is not None and thtien is not None:
                try:
                    derived = round(amount_val - float(thtien))
                    if derived >= 0:
                        return str(derived)
                except (ValueError, TypeError):
                    pass

        # ── 4. Calculate from tax rate × pre-tax amount ──────────────────────
        if thtien is not None and tsuat is not None:
            try:
                thtien_f = float(thtien)
                tsuat_f  = float(tsuat)
                if tsuat_f > 0:
                    return str(round(thtien_f * tsuat_f))
            except (ValueError, TypeError):
                pass

        # ── 5. Tax-exempt items → explicitly 0 ──────────────────────────────
        EXEMPT_LABELS = {"KKKNT", "KCT", "KHAC", "0%"}
        if ltsuat in EXEMPT_LABELS or (tsuat is not None and float(tsuat) == 0):
            return "0"

        # ── 6. khmshdon = 2: Hóa đơn bán hàng (no VAT by law) ───────────────
        if khmshdon == 2:
            return "0"

        # ── 7. No usable data ────────────────────────────────────────────────
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
