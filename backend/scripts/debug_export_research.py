import sys
import os
import json
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.append(os.getcwd())

from backend.database.connection import get_connection

def main():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("--- Checking Tables ---")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [t['table_name'] for t in cur.fetchall()]
        print(f"Tables found: {tables}")
        
        if 'invoice_items' not in tables:
            print("CRITICAL: invoice_items table not found!")
            return

        # Get Item Columns
        cur.execute("SELECT * FROM invoice_items LIMIT 0")
        item_cols = [desc[0] for desc in cur.description]
        print(f"\n--- invoice_items Columns ---\n{item_cols}")

        # Find an invoice that actually has items
        # We need to know the foreign key. Usually it's `invoice_id` or similar.
        # Let's inspect ONE item to see values.
        cur.execute("SELECT * FROM invoice_items LIMIT 1")
        item = cur.fetchone()
        
        if not item:
            print("\nNo items found in invoice_items table.")
        else:
            print(f"\n--- Sample Item ---\n{json.dumps(item, indent=2, default=str)}")
            
            # Try to identify the foreign key
            potential_fks = [k for k, v in item.items() if 'id' in k.lower() and k != 'id']
            print(f"\nPotential Foreign Keys: {potential_fks}")
            
            # If we find a likely FK, try to join
            # Let's guess 'invoice_id' or 'hdon_id'
            
            # Check for matches in invoices
            # Just grab a random invoice and its items if possible
            # Query query: Find an invoice that is referenced in invoice_items
            # Assuming 'invoice_id' exists based on typical patterns, if not we will see from the sample item
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
