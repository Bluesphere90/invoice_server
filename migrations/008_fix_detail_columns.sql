-- Migration: Fix detail column naming (add underscore versions as aliases)
-- The code uses detail_status and detail_retry_count but DB has detailstatus and detailretrycount

-- Add new columns with underscore naming
ALTER TABLE invoices 
ADD COLUMN IF NOT EXISTS detail_status INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS detail_retry_count INTEGER DEFAULT 0;

-- Copy data from old columns to new columns (if any data exists)
UPDATE invoices SET detail_status = detailstatus WHERE detailstatus IS NOT NULL;
UPDATE invoices SET detail_retry_count = detailretrycount WHERE detailretrycount IS NOT NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoices_detail_status ON invoices (detail_status);
CREATE INDEX IF NOT EXISTS idx_invoices_detail_retry ON invoices (detail_retry_count);

-- Remove the update_updated_at trigger from invoices table (it doesn't have updated_at column)
DROP TRIGGER IF EXISTS update_invoices_updated_at ON invoices;
