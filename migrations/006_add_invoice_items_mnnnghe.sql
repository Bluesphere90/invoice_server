-- GDT now returns the item's business-industry code in hdonLquans.
-- Keep the schema aligned so detail persistence does not fail and retry.
ALTER TABLE invoice_items
    ADD COLUMN IF NOT EXISTS mnnnghe TEXT;
