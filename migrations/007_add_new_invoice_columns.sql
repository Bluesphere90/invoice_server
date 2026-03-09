-- Migration: Add new invoice columns from Detail API
-- Added: nmstttoan, nmttttoan, hdcttchinh, dlhquan, dlnhtmai, bltphi, tthdclquan, pdndungs, hdtbssrses, last_downloaded_date

-- Add new columns to invoices table
ALTER TABLE invoices 
ADD COLUMN IF NOT EXISTS nmstttoan TEXT,
ADD COLUMN IF NOT EXISTS nmttttoan TEXT,
ADD COLUMN IF NOT EXISTS hdcttchinh TEXT,
ADD COLUMN IF NOT EXISTS dlhquan TEXT,
ADD COLUMN IF NOT EXISTS dlnhtmai TEXT,
ADD COLUMN IF NOT EXISTS bltphi TEXT,
ADD COLUMN IF NOT EXISTS tthdclquan TEXT,
ADD COLUMN IF NOT EXISTS pdndungs TEXT,
ADD COLUMN IF NOT EXISTS hdtbssrses TEXT,
ADD COLUMN IF NOT EXISTS last_downloaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add indexes for commonly queried columns (optional)
CREATE INDEX IF NOT EXISTS idx_invoices_nmstttoan ON invoices (nmstttoan);
CREATE INDEX IF NOT EXISTS idx_invoices_hdcttchinh ON invoices (hdcttchinh);
CREATE INDEX IF NOT EXISTS idx_invoices_last_downloaded ON invoices (last_downloaded_date);
