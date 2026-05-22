# scratch/explore_all_atm.py
import sqlite3
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"g:\sms\vodacash_monitor\desktop\db\desktop_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT raw_sms FROM transactions").fetchall()

atm_sms = []
for r in rows:
    sms = r["raw_sms"]
    if "atm" in sms.lower() or "صراف" in sms or "ماكينة" in sms or "سحب" in sms:
        if sms.strip() not in atm_sms:
            atm_sms.append(sms.strip())

print(f"Distinct ATM/withdrawal related SMS (count={len(atm_sms)}):")
for idx, sms in enumerate(atm_sms):
    print(f"{idx+1}: {sms}")
conn.close()
