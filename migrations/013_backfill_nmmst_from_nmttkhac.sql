-- Fix missing nmmst for invoices where buyer tax code/id is hidden in nmttkhac JSON array
UPDATE invoices i
SET nmmst = j.new_nmmst
FROM (
    SELECT 
        id,
        agg.el->>'dlieu' as new_nmmst
    FROM (
        SELECT id, nmttkhac::jsonb as nmttkhac_json
        FROM invoices 
        WHERE (nmmst IS NULL OR nmmst = '') 
          AND nmttkhac ILIKE '%AccountObjectIdentificationNumber%'
    ) subq,
    jsonb_array_elements(nmttkhac_json) as agg(el)
    WHERE agg.el->>'ttruong' = 'AccountObjectIdentificationNumber'
) j
WHERE i.id = j.id;
