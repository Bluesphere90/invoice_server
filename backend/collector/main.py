"""
Invoice Collector - Main Entry Point

Multi-company invoice collection service:
1. Loops through all active companies
2. For each company: login → fetch invoices → fetch details
3. Retry logic for failed invoices
"""
import sys
from datetime import date, timedelta

from backend.config import settings
from backend.database import get_connection, init_database, close_connection
from backend.database.repository import InvoiceRepository
from backend.database.item_repository import InvoiceItemRepository
from backend.database.company_repository import CompanyRepository
from backend.collector.http import HoaDonHttpClient, LoginService, ProfileService
from backend.collector.captcha import SvgCaptchaSolver
from backend.collector.invoice import InvoiceListService, InvoiceDetailWorker
from backend.observability import HealthRecorder
from backend.observability.logger import get_logger, configure_root_logger

# Setup root logger (once)
configure_root_logger()

logger = get_logger(__name__)


def collect_for_company(
    company: dict,
    invoice_repo: InvoiceRepository,
    item_repo: InvoiceItemRepository,
    health: HealthRecorder,
    from_date: date,
    to_date: date,
):
    """
    Collect invoices for a single company.
    """
    tax_code = company['tax_code']
    username = company['username']
    password = company['password']
    
    logger.info(f"Processing company: {tax_code}")
    
    # Create new HTTP client for this company
    http_client = HoaDonHttpClient()
    captcha_solver = SvgCaptchaSolver()
    login_service = LoginService(http_client, captcha_solver)
    
    try:
        # Login
        token = login_service.login(username, password)
        logger.info(f"Login successful for {tax_code}")
        
        # Get profile to verify
        profile_service = ProfileService(http_client)
        profile = profile_service.fetch_profile()
        tax_code = profile["tax_code"]
        logger.info(f"Tax code: {tax_code}, Company: {profile['company_name']}")
        
        # Fetch invoices
        list_service = InvoiceListService(http_client, invoice_repo)
        
        # Fetch PURCHASE invoices (hóa đơn đầu vào)
        purchase_ids = list_service.fetch_invoice_identifiers(
            tax_code=tax_code,
            from_date=from_date,
            to_date=to_date,
            is_purchase=True
        )
        logger.info(f"Found {len(purchase_ids)} purchase invoices for {tax_code}")
        health.inc("total_invoices_seen", len(purchase_ids))
        
        # Fetch SOLD invoices (hóa đơn đầu ra)
        sold_ids = list_service.fetch_invoice_identifiers(
            tax_code=tax_code,
            from_date=from_date,
            to_date=to_date,
            is_purchase=False
        )
        logger.info(f"Found {len(sold_ids)} sold invoices for {tax_code}")
        health.inc("total_invoices_seen", len(sold_ids))
        
        # Download details
        detail_worker = InvoiceDetailWorker(http_client, invoice_repo, item_repo)
        
        all_identifiers = purchase_ids + sold_ids
        total = len(all_identifiers)
        
        for i, identifier in enumerate(all_identifiers, 1):
            logger.info(f"Processing detail {i}/{total}: {identifier.id}")
            try:
                detail_worker.process(identifier)
                health.inc("total_detail_success")
            except Exception as e:
                logger.error(f"Detail failed for {identifier.id}: {e}")
                health.inc("total_detail_failed")
        
        return None  # No error
        
    except Exception as e:
        logger.exception(f"Failed to collect for {tax_code}: {e}")
        return str(e)


def retry_failed_invoices(
    invoice_repo: InvoiceRepository,
    item_repo: InvoiceItemRepository,
    http_client: HoaDonHttpClient,
    health: HealthRecorder,
    max_invoices: int = 100,
):
    """
    Retry downloading details for previously failed invoices.
    """
    # TODO: Get failed invoices from DB and retry
    # This needs a method in repository to fetch failed invoices
    logger.info("Retry failed invoices - not yet implemented")


def run_collector():
    """Main collector workflow."""
    logger.info("=" * 60)
    logger.info("Invoice Collector Starting (Multi-Company Mode)")
    logger.info("=" * 60)

    health = HealthRecorder()
    health.mark("last_run_started")

    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()

        conn = get_connection()
        invoice_repo = InvoiceRepository(conn)
        item_repo = InvoiceItemRepository(conn)
        company_repo = CompanyRepository(conn)
        
        # Get all active companies
        companies = company_repo.get_active_companies()
        
        if not companies:
            logger.warning("No active companies found! Adding from .env as fallback...")
            # Fallback: use .env credentials
            if settings.TAX_USERNAME and settings.TAX_PASSWORD:
                company_repo.add_company(
                    tax_code=settings.TAX_USERNAME,
                    username=settings.TAX_USERNAME,
                    password=settings.TAX_PASSWORD,
                    company_name="Default Company (from .env)"
                )
                companies = company_repo.get_active_companies()
        
        logger.info(f"Found {len(companies)} active companies")
        
        # Date range (last 30 days by default)
        to_date = date.today()
        from_date = to_date - timedelta(days=30)
        logger.info(f"Date range: {from_date} to {to_date}")
        
        # Process each company
        for company in companies:
            error = collect_for_company(
                company=company,
                invoice_repo=invoice_repo,
                item_repo=item_repo,
                health=health,
                from_date=from_date,
                to_date=to_date,
            )
            
            # Update company sync status
            company_repo.update_last_sync(company['tax_code'], error)

        health.mark("last_run_completed")
        logger.info("=" * 60)
        logger.info("Invoice Collector Completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"Collector failed: {e}")
        health.error(str(e))
        raise
    finally:
        close_connection()


def main():
    """Entry point."""
    run_collector()


if __name__ == "__main__":
    main()
