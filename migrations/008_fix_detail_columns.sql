-- Migration: Fix detail column naming (add underscore versions as aliases)
-- The code uses detail_status and detail_retry_count but DB has detailstatus and detailretrycount

-- Add new columns with underscore naming
ALTER TABLE invoices 
ADD COLUMN IF NOT EXISTS detail_status INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS detail_retry_count INTEGER DEFAULT 0;

-- NOTE: Removed UPDATE statements that copied from old detailstatus/detailretrycount columns.
-- They caused detail_status to be reset to 0 on every collector run
-- because init_database() re-runs all migrations and detailstatus is never updated by code.

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoices_detail_status ON invoices (detail_status);
CREATE INDEX IF NOT EXISTS idx_invoices_detail_retry ON invoices (detail_retry_count);

-- Remove the update_updated_at trigger from invoices table (it doesn't have updated_at column)
DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
