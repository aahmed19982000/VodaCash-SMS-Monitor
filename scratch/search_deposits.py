# scratch/search_deposits.py
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"desktop/db/desktop_cache.db"
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT raw_sms FROM transactions").fetchall()

print("--- DEPOSIT SMS ---")
seen = set()
for r in rows:
    sms = r[0].strip().replace('\n', ' ')
    if any(kw in sms for kw in ["إيداع", "ايداع", "أودع", "deposit", "atm"]):
        if sms not in seen:
            seen.add(sms)
            print(sms)
conn.close()
