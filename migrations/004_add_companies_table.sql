-- Migration: Add companies table for multi-company support
-- Companies store login credentials for collecting invoices
-- NOTE: This migration is idempotent and matches existing schema

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    tax_code VARCHAR(20) UNIQUE NOT NULL,  -- Mã số thuế (Tax ID)
    company_name VARCHAR(255) NOT NULL,    -- Tên công ty
    username VARCHAR(100) NOT NULL,        -- Username đăng nhập cổng thuế
    password VARCHAR(100) NOT NULL,        -- Password
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,        -- Có đang thu thập không
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_tax_code ON companies (tax_code);
CREATE INDEX IF NOT EXISTS idx_companies_is_active ON companies (is_active);

-- Trigger to update updated_at (only create if function exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger 
            WHERE tgname = 'update_companies_updated_at' 
            AND tgrelid = 'companies'::regclass
        ) THEN
            CREATE TRIGGER update_companies_updated_at
                BEFORE UPDATE ON companies
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        END IF;
    END IF;
END $$;
