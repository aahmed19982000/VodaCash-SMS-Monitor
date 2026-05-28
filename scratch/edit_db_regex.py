# -*- coding: utf-8 -*-
import sys

db_path = r"desktop/db/database.py"

# Read lines in windows-1256
with open(db_path, "r", encoding="windows-1256") as f:
    lines = f.readlines()

# Let's find get_kpi_summary start
start_idx = -1
end_idx = -1
for idx, line in enumerate(lines):
    if "def get_kpi_summary(self, month: str = None)" in line:
        start_idx = idx
    if start_idx != -1 and ").fetchone()" in line:
        end_idx = idx
        break

if start_idx == -1 or end_idx == -1:
    print(f"ERROR: Could not find get_kpi_summary function block. start={start_idx}, end={end_idx}")
    sys.exit(1)

print(f"Found get_kpi_summary function block from line {start_idx+1} to {end_idx+1}")

# Build replacement for this block
new_kpi_block = """    def get_kpi_summary(self, month: str = None, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        \"\"\"إحصائيات (رصيد، دخل، مصاريف) للـ Dashboard\"\"\"
        # إذا لم يُحدد شهر، نستخدم الشهر الحالي بالتوقيت المحلي لضمان الدقة
        filter_params = []
        if start_date and end_date:
            date_filter = "AND date(sms_timestamp) BETWEEN date(?) AND date(?)"
            filter_params = [start_date, end_date]
        elif start_date:
            date_filter = "AND date(sms_timestamp) >= date(?)"
            filter_params = [start_date]
        elif end_date:
            date_filter = "AND date(sms_timestamp) <= date(?)"
            filter_params = [end_date]
        elif month == "ALL":
            date_filter = ""
        else:
            if month:
                date_filter = "AND sms_timestamp LIKE ?"
                filter_params = [f"{month}%"]
            else:
                date_filter = "AND date(sms_timestamp) >= date('now', 'localtime', 'start of month')"
        
        row = self._conn.execute(f\"\"\"
            SELECT
                COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM transactions
            WHERE wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
              {date_filter}
        \"\"\", filter_params).fetchone()
"""

# Replace in list of lines
lines[start_idx : end_idx + 1] = [new_kpi_block]

# Now let's find the tx_rows fetch block (which was after line 470)
# We search for: tx_rows = self._conn.execute(f"""
# and replace it and the next 4 lines
tx_start_idx = -1
tx_end_idx = -1
for idx, line in enumerate(lines):
    if "tx_rows = self._conn.execute(f\"\"\"" in line:
        tx_start_idx = idx
    if tx_start_idx != -1 and "\"\").fetchall()" in line:
        tx_end_idx = idx
        break

if tx_start_idx == -1 or tx_end_idx == -1:
    print(f"ERROR: Could not find tx_rows block. start={tx_start_idx}, end={tx_end_idx}")
    sys.exit(1)

print(f"Found tx_rows block from line {tx_start_idx+1} to {tx_end_idx+1}")

new_tx_block = """        tx_rows = self._conn.execute(f\"\"\"
            SELECT * FROM transactions
            WHERE wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
              {date_filter}
        \"\"\", filter_params).fetchall()
"""

lines[tx_start_idx : tx_end_idx + 1] = [new_tx_block]

# Save lines back in windows-1256
with open(db_path, "w", encoding="windows-1256", newline="\r\n") as f:
    f.writelines(lines)

print("Patch applied successfully!")
