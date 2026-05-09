-- Migration: Backfill tthue from ttkhac for Grab/Taxi invoices
-- Some invoices store item-level tax in ttkhac list under VATAmount key instead of the top-level tthue field.

UPDATE invoice_items
SET tthue = (
    SELECT elem->>'dlieu'
    FROM jsonb_array_elements(ttkhac::jsonb) AS elem
    WHERE elem->>'ttruong' IN (
        'VATAmount', 
        'Tiền thuế', 
        'Tiền thuế dòng (Tiền thuế GTGT)', 
        'Tiền thuế sản phẩm',
        'TThue'
    )
    AND elem->>'dlieu' IS NOT NULL 
    AND elem->>'dlieu' != ''
    LIMIT 1
),
updated_at = CURRENT_TIMESTAMP
WHERE (tthue IS NULL OR tthue = '')
AND ttkhac IS NOT NULL
AND ttkhac::jsonb @> '[{"ttruong": "VATAmount"}]'
OR ttkhac::jsonb @> '[{"ttruong": "Tiền thuế"}]'
OR ttkhac::jsonb @> '[{"ttruong": "Tiền thuế dòng (Tiền thuế GTGT)"}]'
OR ttkhac::jsonb @> '[{"ttruong": "Tiền thuế sản phẩm"}]'
OR ttkhac::jsonb @> '[{"ttruong": "TThue"}]';

