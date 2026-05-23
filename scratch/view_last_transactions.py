import sqlite3
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('desktop/db/desktop_cache.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT * FROM transactions ORDER BY sms_timestamp DESC LIMIT 15").fetchall()

print(f"Found {len(rows)} transactions in the database:\n", flush=True)
for idx, r in enumerate(rows):
    print(f"[{idx+1}] ID: {r['transaction_id']} | Type: {r['type']} | Wallet: {r['wallet_id']} | Counterpart: '{r['counterpart']}'", flush=True)
    print(f"SMS: {r['raw_sms']}", flush=True)
    print("-" * 50, flush=True)
