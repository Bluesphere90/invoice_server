-- Migration: Create invoice_items table
CREATE TABLE IF NOT EXISTS invoice_items (
    id TEXT PRIMARY KEY NOT NULL,
    idhdon TEXT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    
    dgia DOUBLE PRECISION,
    dvtinh TEXT,
    ltsuat TEXT, sluong DOUBLE PRECISION,
    stbchu TEXT,
    stckhau DOUBLE PRECISION,
    stt INTEGER,
    tchat INTEGER,
    ten TEXT,
    thtcthue TEXT,
    thtien DOUBLE PRECISION,
    tlckhau TEXT,
    tsuat DOUBLE PRECISION,
    tthue TEXT,
    sxep INTEGER,
    ttkhac TEXT,
    dvtte TEXT,
    tgia DOUBLE PRECISION,
    tthhdtrung TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_idhdon ON invoice_items (idhdon);

-- Trigger to update updated_at if not already exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_invoice_items_updated_at') THEN
        CREATE TRIGGER update_invoice_items_updated_at
            BEFORE UPDATE ON invoice_items
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
