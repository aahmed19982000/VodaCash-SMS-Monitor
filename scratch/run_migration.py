# scratch/run_migration.py
"""إعادة تحليل جميع العمليات في قاعدة البيانات لتطبيق تصنيف ATM الجديد"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
from mobile.parser.engine import SMSEngine
from shared.models import TransactionType

db_path = r"desktop/db/desktop_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT transaction_id, raw_sms, wallet_id, type FROM transactions").fetchall()
print(f"Total transactions: {len(rows)}")

updated = 0
atm_found = 0
for row in rows:
    tx_id = row["transaction_id"]
    raw_sms = row["raw_sms"]
    old_type = row["type"]
    
    tx = SMSEngine.parse(raw_sms)
    new_type = tx.type.value
    
    # Update if the type changed (especially ATM reclassification)
    if new_type != "UNKNOWN" and new_type != old_type:
        conn.execute(
            "UPDATE transactions SET type=?, balance_after=? WHERE transaction_id=?",
            (new_type, tx.balance_after, tx_id)
        )
        updated += 1
        if "ATM" in new_type:
            atm_found += 1
            print(f"  ATM: [{old_type}] -> [{new_type}] | {raw_sms[:70]}")

conn.commit()
conn.close()
print(f"\nDone! Updated: {updated} transactions, ATM: {atm_found}")

# Show summary
conn2 = sqlite3.connect(db_path)
rows2 = conn2.execute("SELECT type, COUNT(*) as cnt FROM transactions GROUP BY type ORDER BY cnt DESC").fetchall()
print("\nType distribution after migration:")
for r in rows2:
    print(f"  {r[0]:20s}: {r[1]}")
conn2.close()
