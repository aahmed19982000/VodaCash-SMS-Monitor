# scratch/explore_db_sms.py
import sqlite3
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"g:\sms\vodacash_monitor\desktop\db\desktop_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT raw_sms, type, wallet_id FROM transactions").fetchall()

keywords = ["سحب", "خصم", "atm"]
matches = []
for r in rows:
    sms = r["raw_sms"]
    matched = False
    for kw in keywords:
        if kw in sms.lower():
            matched = True
            break
    if matched:
        matches.append((r["type"], r["wallet_id"], sms))

print(f"Total matching transactions: {len(matches)}")
seen = set()
for t, w, sms in matches:
    # Print distinct sms
    clean_sms = sms.strip().replace('\n', ' ')
    if clean_sms not in seen:
        seen.add(clean_sms)
        print(f"[{t}] [{w}] -> {clean_sms}")
conn.close()
