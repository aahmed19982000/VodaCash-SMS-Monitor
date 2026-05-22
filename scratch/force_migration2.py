# scratch/force_migration2.py
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
from mobile.parser.engine import SMSEngine
from shared.models import TransactionType

db_path = r"desktop/db/desktop_cache.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")

rows = conn.execute("SELECT transaction_id, raw_sms, wallet_id, type FROM transactions").fetchall()
print(f"Total: {len(rows)}")

atm_count = 0
for row in rows:
    tx_id = row["transaction_id"]
    raw_sms = row["raw_sms"]
    old_wallet = row["wallet_id"]
    old_type = row["type"]
    
    tx = SMSEngine.parse(raw_sms)
    
    w_id = tx.wallet_id
    if w_id:
        w_id = w_id.strip().lower()
    if not w_id or w_id not in ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "instapay", "bank", "unspecified"]:
        w_id = "unspecified"
    if w_id == "unspecified" and old_wallet:
        old_wallet_clean = old_wallet.strip().lower()
        if old_wallet_clean not in ["wallet_001", "unspecified", ""]:
            w_id = old_wallet_clean
    
    tx_type = tx.type.value if tx.type != TransactionType.UNKNOWN else old_type
    balance_after = tx.balance_after if tx.balance_after >= 0 else None
    
    if tx_id is not None:
        if balance_after is not None:
            conn.execute(
                "UPDATE transactions SET wallet_id=?, type=?, balance_after=? WHERE transaction_id=?",
                (w_id, tx_type, balance_after, tx_id)
            )
        else:
            conn.execute(
                "UPDATE transactions SET wallet_id=?, type=? WHERE transaction_id=?",
                (w_id, tx_type, tx_id)
            )
    else:
        if balance_after is not None:
            conn.execute(
                "UPDATE transactions SET wallet_id=?, type=?, balance_after=? WHERE transaction_id IS NULL AND raw_sms=?",
                (w_id, tx_type, balance_after, raw_sms)
            )
        else:
            conn.execute(
                "UPDATE transactions SET wallet_id=?, type=? WHERE transaction_id IS NULL AND raw_sms=?",
                (w_id, tx_type, raw_sms)
            )
    
    if "ATM" in tx_type:
        atm_count += 1

conn.commit()
conn.execute("PRAGMA wal_checkpoint(FULL)")
conn.close()
print(f"Done! ATM found: {atm_count}")

conn2 = sqlite3.connect(db_path)
rows2 = conn2.execute("SELECT type, COUNT(*) as cnt FROM transactions GROUP BY type ORDER BY cnt DESC").fetchall()
print("\nAfter migration:")
for r in rows2:
    print(f"  {r[0]:25s}: {r[1]}")
conn2.close()
