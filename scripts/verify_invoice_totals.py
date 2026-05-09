
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import PurePath

# Add project root to path
sys.path.append(os.getcwd())

from backend.config import settings

def verify_totals():
    # Use credentials from .env
    # The DSN in settings.DATABASE_URL might be different from local psql access
    # if it uses hostnames like 'db' in docker, but let's try the one from .env
    
    conn = None
    try:
        conn = psycopg2.connect(
            settings.DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        cur = conn.cursor()

        print("Checking data integrity: Item Sum vs Invoice Total")
        print("=" * 60)

        # Query to find invoices where:
        # 1. All items have tthue populated
        # 2. Compare sum(thtien + tthue) with tgtttbso
        # Note: thtien and tthue are stored as DOUBLE PRECISION and TEXT respectively.
        # We need to cast tthue.
        
        sql = """
        WITH item_sums AS (
            SELECT 
                idhdon,
                SUM(COALESCE(thtien, 0)) as sum_thtien,
                SUM(COALESCE(CAST(NULLIF(tthue, '') AS DOUBLE PRECISION), 0)) as sum_tthue,
                COUNT(*) as item_count,
                SUM(CASE WHEN tthue IS NULL OR tthue = '' THEN 1 ELSE 0 END) as missing_tthue_count
            FROM invoice_items
            GROUP BY idhdon
        )
        SELECT 
            i.id,
            i.shdon,
            i.nbten,
            i.tgtttbso,
            s.sum_thtien,
            s.sum_tthue,
            (s.sum_thtien + s.sum_tthue) as calculated_total,
            ABS(i.tgtttbso - (s.sum_thtien + s.sum_tthue)) as diff
        FROM invoices i
        JOIN item_sums s ON i.id = s.idhdon
        WHERE s.missing_tthue_count = 0  -- Skip invoices with any missing tthue
        AND i.tgtttbso > 0              -- Skip zero-total invoices
        ORDER BY diff DESC
        LIMIT 20;
        """

        cur.execute(sql)
        rows = cur.fetchall()

        if not rows:
            print("No invoices found with complete tthue data to check.")
            return

        print(f"{'Inv #':<10} | {'Expected':<12} | {'Calculated':<12} | {'Diff':<10} | {'Status'}")
        print("-" * 60)

        match_count = 0
        mismatch_count = 0
        epsilon = 2.0 # Allow for small rounding differences (e.g. 1-2 VND)

        for row in rows:
            expected = row['tgtttbso']
            calculated = row['calculated_total']
            diff = row['diff']
            
            status = "✅ OK" if diff <= epsilon else "❌ MISMATCH"
            if diff <= epsilon:
                match_count += 1
            else:
                mismatch_count += 1
            
            print(f"{row['shdon']:<10} | {expected:12,.0f} | {calculated:12,.0f} | {diff:10,.2f} | {status}")

        # Summary statistics
        cur.execute("""
            SELECT 
                COUNT(DISTINCT i.id) as total_checked,
                SUM(CASE WHEN ABS(i.tgtttbso - (s.sum_thtien + s.sum_tthue)) <= 2 THEN 1 ELSE 0 END) as matches
            FROM invoices i
            JOIN (
                SELECT idhdon, SUM(thtien) as sum_thtien, 
                       SUM(CAST(NULLIF(tthue, '') AS DOUBLE PRECISION)) as sum_tthue,
                       SUM(CASE WHEN tthue IS NULL OR tthue = '' THEN 1 ELSE 0 END) as missing_count
                FROM invoice_items
                GROUP BY idhdon
            ) s ON i.id = s.idhdon
            WHERE s.missing_count = 0 AND i.tgtttbso > 0
        """)
        stats = cur.fetchone()
        
        print("-" * 60)
        print(f"Total checked (with full tthue): {stats['total_checked']}")
        print(f"Total matches: {stats['matches']}")
        if stats['total_checked'] > 0:
            print(f"Accuracy: {(stats['matches']/stats['total_checked'])*100:.2f}%")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_totals()
