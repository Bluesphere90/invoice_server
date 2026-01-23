#!/usr/bin/env python3
"""
Test rate limit for INVOICE DETAIL endpoint specifically.
This is the endpoint that gets called 384 times (once per invoice).
"""
import time
import sys
import os

os.chdir('/home/tran-ninh/OtherProjects/invoice_server')
sys.path.insert(0, '/home/tran-ninh/OtherProjects/invoice_server')

import requests
from backend.collector.captcha.svg_solver import SvgCaptchaSolver

BASE_URL = "https://hoadondientu.gdt.gov.vn:30000"

def test_detail_rate_limit():
    """Test rate limit specifically for /query/invoices/detail endpoint."""
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
    })
    
    print("="*60)
    print("GDT SERVER - INVOICE DETAIL RATE LIMIT TEST")
    print("="*60)
    
    # --- Login ---
    print("\n1. Logging in...")
    resp = session.get(f"{BASE_URL}/captcha", timeout=30)
    captcha_data = resp.json()
    
    # Try different field names for captcha SVG
    svg_content = captcha_data.get("svg") or captcha_data.get("data") or captcha_data.get("content") or ""
    if not svg_content and isinstance(captcha_data, dict):
        # Try to find any string value that looks like SVG
        for k, v in captcha_data.items():
            if isinstance(v, str) and "<svg" in v.lower():
                svg_content = v
                break
    
    solver = SvgCaptchaSolver()
    captcha_value = solver.solve(svg_content)
    
    login_payload = {
        "username": "0311721886",
        "password": "Crif@1234",
        "cvalue": captcha_value,
        "ckey": captcha_data["key"]
    }
    resp = session.post(f"{BASE_URL}/security-taxpayer/authenticate", json=login_payload, timeout=30)
    result = resp.json()
    
    if resp.status_code != 200 or "token" not in result:
        print(f"Login failed: {result}")
        return
    
    session.headers["Authorization"] = f"Bearer {result['token']}"
    print("   Login successful!")
    
    # --- Get some invoice IDs from database ---
    print("\n2. Getting invoice IDs from database...")
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(
        host="localhost",
        database="invoice_db",
        user="invoice_user", 
        password="Concobebe123@"
    )
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nbmst, khhdon, shdon, khmshdon 
            FROM invoices 
            WHERE nbmst IS NOT NULL AND khhdon IS NOT NULL
            LIMIT 30
        """)
        invoices = cur.fetchall()
    
    conn.close()
    
    if not invoices:
        print("   No invoices found in database!")
        return
    
    print(f"   Found {len(invoices)} invoices to test with")
    
    # --- Test configurations ---
    test_configs = [
        {"delay": 0, "count": 15, "name": "No delay (rapid fire)"},
        {"delay": 1.0, "count": 15, "name": "1.0s delay"},
        {"delay": 1.5, "count": 15, "name": "1.5s delay"},
    ]
    
    results = []
    invoice_idx = 0
    
    for config in test_configs:
        delay = config["delay"]
        count = config["count"]
        
        print(f"\n{'='*50}")
        print(f"TEST: {config['name']} ({count} DETAIL requests)")
        print(f"{'='*50}")
        
        success_count = 0
        error_count = 0
        connection_errors = 0
        response_times = []
        
        for i in range(count):
            # Use different invoice for each request (realistic scenario)
            inv = invoices[invoice_idx % len(invoices)]
            invoice_idx += 1
            
            # Build detail URL (same as InvoiceDetailWorker uses)
            detail_url = f"{BASE_URL}/query/invoices/detail?nbmst={inv['nbmst']}&khhdon={inv['khhdon']}&shdon={inv['shdon']}&khmshdon={inv['khmshdon']}"
            
            start = time.time()
            try:
                resp = session.get(detail_url, timeout=30)
                elapsed = time.time() - start
                response_times.append(elapsed)
                
                if resp.status_code == 200:
                    success_count += 1
                    status = "OK"
                elif resp.status_code == 429:
                    error_count += 1
                    status = "RATE LIMITED"
                else:
                    error_count += 1
                    status = f"HTTP {resp.status_code}"
                    
                print(f"  [{i+1:2d}] {status} ({elapsed:.2f}s) - HĐ #{inv['shdon']}")
                
            except requests.exceptions.ConnectionError:
                elapsed = time.time() - start
                connection_errors += 1
                print(f"  [{i+1:2d}] CONNECTION ERROR ({elapsed:.2f}s)")
                if connection_errors >= 3:
                    print("  >>> Too many connection errors, stopping test")
                    break
                    
            except Exception as e:
                elapsed = time.time() - start
                error_count += 1
                print(f"  [{i+1:2d}] ERROR: {type(e).__name__} ({elapsed:.2f}s)")
            
            if delay > 0:
                time.sleep(delay)
        
        total = success_count + error_count + connection_errors
        avg_time = sum(response_times) / len(response_times) if response_times else 0
        
        result = {
            "name": config["name"],
            "delay": delay,
            "success": success_count,
            "total": total,
            "conn_errors": connection_errors,
            "avg_time": avg_time
        }
        results.append(result)
        
        print(f"\n  RESULT: {success_count}/{total} success, {connection_errors} conn errors")
        print(f"  Avg response time: {avg_time:.2f}s")
        
        if connection_errors > 0:
            print("  Waiting 30s before next test...")
            time.sleep(30)
        else:
            time.sleep(5)
    
    # --- Summary ---
    print("\n" + "="*60)
    print("SUMMARY - INVOICE DETAIL ENDPOINT")
    print("="*60)
    for r in results:
        rate = r['success'] / r['total'] * 100 if r['total'] > 0 else 0
        print(f"  {r['name']}: {r['success']}/{r['total']} ({rate:.0f}%), {r['conn_errors']} conn errors")
    
    print("\n" + "="*60)
    print("RECOMMENDATION FOR DETAIL_WORKER")
    print("="*60)
    
    best = max(results, key=lambda x: (x['success'] / max(x['total'], 1), -x['conn_errors']))
    if best['conn_errors'] == 0:
        print(f"  ✅ Optimal delay: {best['delay']}s between DETAIL requests")
    else:
        print(f"  ⚠️ All tests had errors - recommend 2s delay + retry logic")

if __name__ == "__main__":
    test_detail_rate_limit()
