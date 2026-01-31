"""
Verification script for the new Excel export with flattened invoice data.
"""
import sys
import os
sys.path.append(os.getcwd())

from backend.database.connection import get_connection

def main():
    conn = get_connection()
    
    # Test the SQL query used in export
    sql = """
        SELECT 
            -- Invoice header info
            i.khhdon, i.shdon, i.tdlap, i.dvtte, i.tgia,
            i.nbten, i.nbmst, i.nbdchi, i.nky, i.mhdon, i.ncma,
            i.nmten, i.nmmst, i.nmdchi,
            -- Invoice totals
            i.tgtcthue, i.tgtthue, i.tgtttbso,
            -- Invoice status
            i.khmshdon, i.tthai,
            -- Item detail
            ii.stt AS item_stt, ii.tchat, ii.mhhdvu, ii.ten AS item_ten,
            ii.dvtinh, ii.sluong, ii.dgia, ii.tlckhau, ii.stckhau,
            ii.ltsuat, ii.tsuat, ii.thtien,
            CAST(NULLIF(ii.tthue, '') AS DOUBLE PRECISION) AS item_tthue,
            (COALESCE(ii.thtien, 0) + COALESCE(CAST(NULLIF(ii.tthue, '') AS DOUBLE PRECISION), 0)) AS thtcthue
        FROM invoices i
        LEFT JOIN invoice_items ii ON i.id = ii.idhdon
        ORDER BY i.tdlap DESC NULLS LAST, i.shdon DESC NULLS LAST, ii.stt ASC NULLS LAST
        LIMIT 5
    """
    
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        
    print(f"Query returned {len(rows)} rows")
    print("-" * 80)
    
    for i, row in enumerate(rows, 1):
        data = dict(row)
        print(f"\n--- Row {i} ---")
        print(f"Invoice: {data.get('shdon')} | {data.get('khhdon')} | {data.get('tdlap')}")
        print(f"Seller: {data.get('nbten')} ({data.get('nbmst')})")
        print(f"Buyer: {data.get('nmten')} ({data.get('nmmst')})")
        print(f"Totals: {data.get('tgtcthue')} + {data.get('tgtthue')} = {data.get('tgtttbso')}")
        print(f"Status: khmshdon={data.get('khmshdon')}, tthai={data.get('tthai')}")
        print(f"Item #{data.get('item_stt')}: {data.get('item_ten')}")
        print(f"  Qty: {data.get('sluong')} x {data.get('dgia')} = {data.get('thtien')}")
        print(f"  Tax: {data.get('ltsuat')} ({data.get('tsuat')}) => {data.get('item_tthue')}")
    
    conn.close()
    print("\n✅ Verification complete!")

if __name__ == "__main__":
    main()
