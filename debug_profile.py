import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import get_connection, init_database
from backend.database.company_repository import CompanyRepository
from backend.collector.http import HoaDonHttpClient, LoginService, ProfileService
from backend.collector.captcha import SvgCaptchaSolver

# Configure logging to show info
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_profile(tax_code):
    print(f"--- Debugging Profile for {tax_code} ---")
    
    # 1. Get credentials
    init_database()
    conn = get_connection()
    repo = CompanyRepository(conn)
    company = repo.get_company_with_password(tax_code)
    
    if not company:
        print(f"Error: Company {tax_code} not found in database.")
        return

    print(f"Found company in DB. Username: {company['username']}")
    
    # 2. Login
    try:
        http_client = HoaDonHttpClient()
        captcha_solver = SvgCaptchaSolver()
        login_service = LoginService(http_client, captcha_solver)
        
        print("Logging in...")
        login_service.login(company['username'], company['password'])
        print("Login successful.")
        
        # 3. Fetch Profile
        print("Fetching profile...")
        profile_service = ProfileService(http_client)
        
        # We want to see the RAW response, so we might need to access the internal http client or modified ProfileService
        # But ProfileService.fetch_profile() returns a dict that includes "raw".
        # Let's check ProfileService implementation again.
        # It returns:
        # {
        #     "tax_code": ...,
        #     "company_name": raw.get("name"),
        #     "authorities": ...,
        #     "raw": raw,
        # }
        
        profile = profile_service.fetch_profile()
        
        print("\n--- Processed Profile ---")
        print(f"Tax Code: {profile.get('tax_code')}")
        print(f"Company Name (parsed): {profile.get('company_name')}")
        
        print("\n--- Raw Profile JSON ---")
        print(json.dumps(profile.get('raw'), indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_profile("0111263861")
