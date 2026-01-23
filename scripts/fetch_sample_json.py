"""
Script to fetch sample invoice JSON from API to see exact column names.
"""
import json
from backend.collector.http import HoaDonHttpClient, LoginService, ProfileService
from backend.collector.captcha import SvgCaptchaSolver
from backend.collector.http.endpoints import BASE_URL
from backend.config import settings

def fetch_sample():
    # Login
    http_client = HoaDonHttpClient()
    captcha_solver = SvgCaptchaSolver()
    login_service = LoginService(http_client, captcha_solver)
    
    token = login_service.login(settings.TAX_USERNAME, settings.TAX_PASSWORD)
    print("Login successful!")
    
    # Get profile
    profile_service = ProfileService(http_client)
    profile = profile_service.fetch_profile()
    print(f"Tax code: {profile['tax_code']}")
    
    # Fetch one invoice list
    url = f"{BASE_URL}/query/invoices/purchase?sort=tdlap:desc&size=2&search=tdlap=ge=01/01/2026T00:00:00;tdlap=le=20/01/2026T23:59:59"
    
    resp = http_client.session.get(url)
    data = resp.json()
    
    print("\n" + "="*60)
    print("SAMPLE INVOICE LIST RESPONSE (first invoice):")
    print("="*60)
    
    if data.get("datas"):
        invoice_summary = data["datas"][0]
        print(json.dumps(invoice_summary, indent=2, ensure_ascii=False))
        
        # Get column names
        print("\n" + "="*60)
        print("COLUMN NAMES FROM LIST API (sorted):")
        print("="*60)
        columns = sorted(invoice_summary.keys())
        for col in columns:
            print(f"  '{col}',")
        
        # Fetch detail for this invoice
        inv_id = invoice_summary["id"]
        nbmst = invoice_summary.get("nbmst", "")
        khhdon = invoice_summary.get("khhdon", "")
        shdon = invoice_summary.get("shdon", "")
        khmshdon = invoice_summary.get("khmshdon", "")
        
        detail_url = f"{BASE_URL}/query/invoices/detail?nbmst={nbmst}&khhdon={khhdon}&shdon={shdon}&khmshdon={khmshdon}"
        detail_resp = http_client.session.get(detail_url)
        detail_data = detail_resp.json()
        
        print("\n" + "="*60)
        print("SAMPLE INVOICE DETAIL RESPONSE:")
        print("="*60)
        print(json.dumps(detail_data, indent=2, ensure_ascii=False))
        
        print("\n" + "="*60)
        print("COLUMN NAMES FROM DETAIL API (sorted):")
        print("="*60)
        detail_columns = sorted(detail_data.keys())
        for col in detail_columns:
            print(f"  '{col}',")
    else:
        print("No invoices found")

if __name__ == "__main__":
    fetch_sample()
