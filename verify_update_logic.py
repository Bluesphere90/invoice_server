import sys
import os
import time
from datetime import date
import logging

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_connection, init_database
from backend.database.company_repository import CompanyRepository
from backend.collector.job_manager import run_collector_job, JobManager

# Configure logging
logging.basicConfig(level=logging.INFO)

def verify_logic(tax_code):
    print(f"--- Verifying Logic for {tax_code} ---")
    
    # 1. Get credentials
    init_database()
    conn = get_connection()
    repo = CompanyRepository(conn)
    company = repo.get_company_with_password(tax_code)
    
    if not company:
        print("Company not found")
        return

    print("Running collector job directly...")
    
    # Mock date range (just today to be fast)
    today = date.today()
    
    # Run job (this is synchronous in this script, though it spawns internal threads if any, 
    # but run_collector_job is the target function itself)
    # run_collector_job creates a manager and updates job status. 
    # We need to make sure manager doesn't crash.
    
    # Create a job first so manager has it
    manager = JobManager()
    job = manager.create_job(tax_code, today, today)
    
    try:
        run_collector_job(job.job_id, company, today, today)
        print("Job finished.")
    except Exception as e:
        print(f"Job failed: {e}")
        import traceback
        traceback.print_exc()

    # Check DB
    updated_company = repo.get_company_by_tax_code(tax_code)
    print(f"Company Name in DB: '{updated_company['company_name']}'")

if __name__ == "__main__":
    verify_logic("0111263861")
