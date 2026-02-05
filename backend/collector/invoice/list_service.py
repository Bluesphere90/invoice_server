import logging
import time
import random
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from backend.collector.invoice.types import InvoiceIdentifier
from backend.collector.http.endpoints import BASE_URL
from backend.observability.logger import get_logger

logger = get_logger(__name__)

# Retry configuration
MAX_RETRY_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 2
MAX_BACKOFF_SECONDS = 120  # 2 minutes max wait


class InvoiceListService:
    """
    Fetch invoice summaries (metadata only).
    Ported from InvoiceWindow.xaml.cs:
      - DownloadInvoicesAsync
      - GetInvoiceSummariesAsync
    """

    def __init__(self, http_client, invoice_repo):
        """
        http_client: HoaDonHttpClient (requests.Session wrapper)
        invoice_repo: InvoiceRepository (Postgres)
        """
        self.http = http_client
        self.repo = invoice_repo

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def fetch_invoice_identifiers(
        self,
        tax_code: str,
        from_date: date,
        to_date: date,
        is_purchase: bool,
        ignore_saved: bool = True,
    ) -> List[InvoiceIdentifier]:
        """
        Main entrypoint.
        """
        periods = self._split_by_month(from_date, to_date)

        identifiers: List[InvoiceIdentifier] = []

        for start, end in periods:
            logger.info(
                "Fetching invoices %s [%s → %s]",
                "PURCHASE" if is_purchase else "SOLD",
                start,
                end,
            )

            # 1️⃣ query/*
            identifiers.extend(
                self._fetch_one_period(
                    tax_code,
                    start,
                    end,
                    is_purchase,
                    is_sco=False,
                    ignore_saved=ignore_saved,
                )
            )

            # 2️⃣ sco-query/*
            identifiers.extend(
                self._fetch_one_period(
                    tax_code,
                    start,
                    end,
                    is_purchase,
                    is_sco=True,
                    ignore_saved=ignore_saved,
                )
            )

        logger.info("Total invoice identifiers collected: %d", len(identifiers))
        return identifiers

    # ------------------------------------------------------------------
    # CORE LOGIC
    # ------------------------------------------------------------------

    def _fetch_one_period(
        self,
        tax_code: str,
        start: date,
        end: date,
        is_purchase: bool,
        is_sco: bool,
        ignore_saved: bool,
    ) -> List[InvoiceIdentifier]:

        base_path = self._build_base_path(is_purchase, is_sco)

        search = self._build_search(start, end)
        sort = "tdlap:desc"

        params = {
            "sort": sort,
            "size": 50,
            "search": search,
        }

        url = f"{BASE_URL}{base_path}?{urlencode(params)}"
        results: List[InvoiceIdentifier] = []

        while url:
            data = self._fetch_with_retry(url)
            if data is None:
                logger.error("Stop pagination: Failed for url %s", url)
                break

            invoices = data.get("datas") or []
            logger.info("Fetched %d invoices from page", len(invoices))
            
            for inv in invoices:
                self._process_invoice(
                    inv,
                    is_sco,
                    ignore_saved,
                    results,
                )

            url = self._next_page(url, data.get("state"))

        return results

    def _fetch_with_retry(self, url: str) -> Optional[dict]:
        """
        Fetch URL with exponential backoff retry for rate limiting (429) 
        and transient errors (5xx).
        """
        backoff = INITIAL_BACKOFF_SECONDS
        
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                logger.debug("GET %s (attempt %d/%d)", url, attempt, MAX_RETRY_ATTEMPTS)
                resp = self.http.session.get(url, timeout=30)
                
                if resp.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = resp.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = backoff
                    
                    # Add jitter to prevent thundering herd
                    wait_time += random.uniform(0, 2)
                    wait_time = min(wait_time, MAX_BACKOFF_SECONDS)
                    
                    logger.warning(
                        "Rate limited (429). Waiting %.1f seconds before retry %d/%d",
                        wait_time, attempt, MAX_RETRY_ATTEMPTS
                    )
                    time.sleep(wait_time)
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue
                
                if resp.status_code >= 500:
                    # Server error - wait and retry
                    wait_time = backoff + random.uniform(0, 2)
                    logger.warning(
                        "Server error (%d). Waiting %.1f seconds before retry %d/%d",
                        resp.status_code, wait_time, attempt, MAX_RETRY_ATTEMPTS
                    )
                    time.sleep(wait_time)
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue
                
                resp.raise_for_status()
                return resp.json()
                
            except requests.exceptions.Timeout:
                wait_time = backoff + random.uniform(0, 2)
                logger.warning(
                    "Request timeout. Waiting %.1f seconds before retry %d/%d",
                    wait_time, attempt, MAX_RETRY_ATTEMPTS
                )
                time.sleep(wait_time)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                
            except requests.exceptions.ConnectionError as e:
                wait_time = backoff + random.uniform(0, 2)
                logger.warning(
                    "Connection error: %s. Waiting %.1f seconds before retry %d/%d",
                    str(e), wait_time, attempt, MAX_RETRY_ATTEMPTS
                )
                time.sleep(wait_time)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                
            except requests.exceptions.RequestException as e:
                logger.error("Request failed: %s", str(e))
                raise
        
        logger.error("Max retry attempts (%d) exceeded for URL: %s", MAX_RETRY_ATTEMPTS, url)
        return None


    # ------------------------------------------------------------------
    # INVOICE PROCESSING
    # ------------------------------------------------------------------

    def _process_invoice(
        self,
        inv: dict,
        is_sco: bool,
        ignore_saved: bool,
        out: List[InvoiceIdentifier],
    ):
        invoice_id = inv["id"]

        exists = self.repo.invoice_header_exists(invoice_id)

        # --- SAVE SUMMARY ---
        if not exists or not ignore_saved:
            self.repo.upsert_invoice_summary(inv)

        # --- ADD TO PIPELINE ---
        should_add = (
            not exists
            or not ignore_saved
            or self.repo.should_retry_detail(invoice_id)
        )

        if not should_add:
            return

        identifier = InvoiceIdentifier(
            id=invoice_id,
            nbmst=inv["nbmst"],
            khhdon=inv["khhdon"],
            shdon=inv["shdon"],
            khmshdon=inv["khmshdon"],
            tdlap=self._parse_datetime(inv["tdlap"]),
            is_sco=is_sco,
        )

        out.append(identifier)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _build_base_path(is_purchase: bool, is_sco: bool) -> str:
        if is_sco:
            return (
                "/sco-query/invoices/purchase"
                if is_purchase
                else "/sco-query/invoices/sold"
            )
        return (
            "/query/invoices/purchase"
            if is_purchase
            else "/query/invoices/sold"
        )

    @staticmethod
    def _build_search(start: date, end: date) -> str:
        return (
            f"tdlap=ge={start:%d/%m/%Y}T00:00:00;"
            f"tdlap=le={end:%d/%m/%Y}T23:59:59"
        )

    @staticmethod
    def _split_by_month(start: date, end: date) -> List[Tuple[date, date]]:
        periods = []
        cursor = start

        while cursor <= end:
            month_end = date(
                cursor.year,
                cursor.month,
                _days_in_month(cursor.year, cursor.month),
            )

            periods.append((cursor, min(month_end, end)))

            # Nhảy sang tháng tiếp theo (safe cho mọi tháng)
            cursor = (month_end + timedelta(days=1)).replace(day=1)

        return periods

    @staticmethod
    def _next_page(current_url: str, state: Optional[str]) -> Optional[str]:
        if not state:
            return None

        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query)
        qs["state"] = state

        return f"{BASE_URL}{parsed.path}?{urlencode(qs, doseq=True)}"

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _days_in_month(year: int, month: int) -> int:
    from calendar import monthrange
    return monthrange(year, month)[1]
