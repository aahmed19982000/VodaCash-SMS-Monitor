# scratch/search_instapay.py
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"desktop/db/desktop_cache.db"
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT raw_sms, type FROM transactions WHERE wallet_id='instapay'").fetchall()

print("--- INSTAPAY SMS ---")
seen = set()
for r in rows:
    sms = r[0].strip().replace('\n', ' ')
    if sms not in seen:
        seen.add(sms)
        print(f"[{r[1]}] -> {sms}")
conn.close()
