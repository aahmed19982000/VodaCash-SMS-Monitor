# scratch/check_tx_ids.py
import sys, sqlite3
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("desktop/db/desktop_cache.db")
# Check if transaction IDs are NULL
null_ids = conn.execute("SELECT COUNT(*) FROM transactions WHERE transaction_id IS NULL").fetchone()[0]
print(f"NULL transaction_ids: {null_ids}")

# Check some
sample = conn.execute("SELECT transaction_id, type FROM transactions LIMIT 5").fetchall()
for r in sample:
    print(f"  ID: {repr(r[0])[:30]} | Type: {r[1]}")

# What type are sah ATM candidates?  
sah_sample = conn.execute("SELECT transaction_id, type, raw_sms FROM transactions WHERE raw_sms LIKE '%من محفظة%' LIMIT 3").fetchall()
print("\nWallet ATM candidates:")
for r in sah_sample:
    print(f"  tx_id={repr(r[0])[:20]} | type={r[1]} | sms={r[2][:50]}")
conn.close()
