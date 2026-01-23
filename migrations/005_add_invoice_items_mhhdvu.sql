-- Migration: Add missing mhhdvu column to invoice_items
-- Attempt to fix missing column error

ALTER TABLE invoice_items ADD COLUMN IF NOT EXISTS mhhdvu TEXT;
