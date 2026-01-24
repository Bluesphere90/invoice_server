import sys
import os
sys.path.append(os.getcwd())

from backend.database import get_connection
from backend.database.company_repository import CompanyRepository

def check_company(tax_code):
    conn = get_connection()
    repo = CompanyRepository(conn)
    company = repo.get_company_by_tax_code(tax_code)
    
    if company:
        print(f"Company found: {company['company_name']}")
        print(f"Is Active: {company.get('is_active')}")
        print(f"Username: {company.get('username')}")
    else:
        print("Company not found")

if __name__ == "__main__":
    check_company("0111263861")
