# scratch/check_atm_count.py
import sys, sqlite3
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("desktop/db/desktop_cache.db")
rows = conn.execute("SELECT type, COUNT(*) as cnt FROM transactions GROUP BY type ORDER BY cnt DESC").fetchall()
print("Current type distribution:")
for r in rows:
    print(f"  {r[0]:25s}: {r[1]}")

print("\nATM samples:")
atm_rows = conn.execute("SELECT raw_sms FROM transactions WHERE type='ATM_WITHDRAWAL' LIMIT 5").fetchall()
for r in atm_rows:
    print(f"  {r[0][:80]}")
conn.close()
