# scratch/check_instapay_row.py
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_path = r"g:\sms\vodacash_monitor\desktop\db\desktop_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
r = conn.execute("SELECT * FROM transactions WHERE raw_sms LIKE '%ATM%'").fetchone()
if r:
    for k in r.keys():
        val = r[k]
        print(f"{k}: {val}")
else:
    print("Not found")
conn.close()
