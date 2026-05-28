# scratch/fix_db_kpi.py
import os

filepath = 'desktop/db/database.py'

# 1. Read existing code
with open(filepath, 'r', encoding='windows-1256') as f:
    text = f.read()

# 2. Find start of get_kpi_summary and start of calculate_fee
start = text.find('    def get_kpi_summary')
end = text.find('    def calculate_fee')

if start != -1 and end != -1:
    # 3. Build new method string
    new_method = '''    def get_kpi_summary(self, month: str = None, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """إحصائيات (رصيد، دخل، مصاريف) للـ Dashboard"""
        # بناء شرط التاريخ والبارامترات
        query_cond = "1=1"
        params = []
        
        if start_date:
            query_cond += " AND date(sms_timestamp) >= date(?)"
            params.append(start_date)
            
        if end_date:
            query_cond += " AND date(sms_timestamp) <= date(?)"
            params.append(end_date)
            
        if not start_date and not end_date:
            if month == "ALL":
                pass # لا نضع شرطاً
            elif month:
                query_cond += " AND sms_timestamp LIKE ?"
                params.append(f"{month}%")
            else:
                # الافتراضي الشهر الحالي
                query_cond += " AND date(sms_timestamp) >= date('now', 'localtime', 'start of month')"
        
        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM transactions
            WHERE {query_cond}
              AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
        """, params).fetchone()
        
        # حساب رصيد كل محفظة
        wallet_balances = {}
        supported_wallets = ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "bank"]
        
        for w_id in supported_wallets:
            # 1. تحقق مما إذا كان هناك رصيد ابتدائي يدوي في الإعدادات
            initial_bal_str = self.get_setting(f"initial_balance_{w_id}", None)
            
            # 2. تحقق مما إذا كان هناك معاملات لهذه المحفظة
            has_tx = self._conn.execute(
                "SELECT 1 FROM transactions WHERE wallet_id = ? LIMIT 1", (w_id,)
            ).fetchone()
            
            # نعرض المحفظة فقط إذا كان لها رصيد يدوي أو معاملات مسجلة
            if initial_bal_str is not None or has_tx is not None:
                # حساب صافي التغيير من المعاملات في قاعدة البيانات
                tx_sum = self._conn.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS net_change
                    FROM transactions
                    WHERE wallet_id = ?
                """, (w_id,)).fetchone()
                net_change = tx_sum["net_change"] if tx_sum else 0.0
 
                if initial_bal_str is not None:
                    # إذا تم إدخال رصيد ابتدائي يدوي:
                    try:
                        balance_raw = float(initial_bal_str) + net_change
                    except ValueError:
                        balance_raw = 0.0 + net_change
                else:
                    # إذا لم يوجد رصيد يدوي، نبحث عن آخر معاملة تحتوي على رصيد تلقائي من الرسالة (>= 0)
                    latest_bal_row = self._conn.execute("""
                        SELECT balance_after 
                        FROM transactions 
                        WHERE wallet_id = ? AND balance_after >= 0 
                        ORDER BY sms_timestamp DESC, received_at DESC, transaction_id DESC 
                        LIMIT 1
                    """, (w_id,)).fetchone()
                    
                    if latest_bal_row:
                        balance_raw = latest_bal_row["balance_after"]
                    else:
                        # إذا لم يوجد رصيد تلقائي في الرسائل، نبدأ من 0 + صافي المعاملات
                        balance_raw = 0.0 + net_change
                
                # نعرض الرصيد الفعلي للمحفظة في الحسابات بالصفحة الرئيسية دون طرح الأرباح المعلقة
                wallet_balances[w_id] = balance_raw
            
        current_balance = sum(wallet_balances.values())
 
        # حساب إجمالي الرسوم للفترة المحددة
        tx_rows = self._conn.execute(f"""
            SELECT * FROM transactions
            WHERE {query_cond}
              AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
        """, params).fetchall()
        
        total_fees = 0.0
        wallet_fees = {}
        profit_cash = 0.0
        profit_in_wallet = 0.0
        profit_unset = 0.0
        for r in tx_rows:
            tx = self._row_to_transaction(r)
            fee = self.calculate_fee(tx)
            total_fees += fee
            w_id = tx.wallet_id
            if w_id:
                w_id = w_id.strip().lower()
                wallet_fees[w_id] = wallet_fees.get(w_id, 0.0) + fee
            
            p_status = r["profit_status"] if "profit_status" in r.keys() else "UNSET"
            if p_status == "CASH":
                profit_cash += fee
            elif p_status == "IN_WALLET":
                profit_in_wallet += fee
            else:
                profit_unset += fee
 
        return {
            "income": row["total_income"],
            "expenses": row["total_expenses"],
            "transactions_count": row["total_transactions"],
            "current_balance": current_balance,
            "wallet_balances": wallet_balances,
            "fees": total_fees,
            "wallet_fees": wallet_fees,
            "profit_cash": profit_cash,
            "profit_in_wallet": profit_in_wallet,
            "profit_unset": profit_unset
        }

'''
    
    # 4. Perform the replacement
    new_text = text[:start] + new_method + text[end:]
    with open(filepath, 'w', encoding='windows-1256', newline='\r\n') as f:
        f.write(new_text)
    print("Success: database.py updated successfully!")
else:
    print("Error: Could not locate get_kpi_summary or calculate_fee in database.py")
