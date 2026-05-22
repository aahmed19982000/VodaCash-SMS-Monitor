# desktop/db/database.py
# ── SQLite Local Cache لسطح المكتب ────────────────────────────────────────

import sqlite3
import threading
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict

from shared.models import Transaction, TransactionType

logger = logging.getLogger("VodaCash.DesktopDB")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DESKTOP_DB_PATH = os.path.join(BASE_DIR, "desktop", "db", "desktop_cache.db")


class DesktopDatabase:
    """
    قاعدة بيانات محلية لسطح المكتب.
    تُخزن العمليات الواردة من الموبايل عبر الـ WebSocket وتُستخدم لعرضها في الـ Dashboard والفلترة.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """Singleton"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        self._db_path = db_path or DESKTOP_DB_PATH
        self._local = threading.local()
        self._ensure_dir()
        self._create_tables()
        self._initialized = True
        logger.info(f"✅ Desktop Database initialized: {self._db_path}")

    # ═════════════════════════════════════════════════════════════════════
    # الاتصال
    # ═════════════════════════════════════════════════════════════════════

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    # ═════════════════════════════════════════════════════════════════════
    # بناء الجداول
    # ═════════════════════════════════════════════════════════════════════

    def _create_tables(self):
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id  TEXT PRIMARY KEY,
                type            TEXT    NOT NULL,
                amount          REAL    NOT NULL,
                balance_after   REAL    NOT NULL,
                counterpart     TEXT    DEFAULT '',
                raw_sms         TEXT    NOT NULL,
                parsed_at       TEXT    NOT NULL,
                sms_timestamp   TEXT    NOT NULL,
                confidence      REAL    NOT NULL,
                wallet_id       TEXT    DEFAULT '',
                received_at     TEXT    DEFAULT (datetime('now'))
            );
            
            -- فهارس للفلترة السريعة
            CREATE INDEX IF NOT EXISTS idx_type ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_sms_timestamp ON transactions(sms_timestamp);
            CREATE INDEX IF NOT EXISTS idx_amount ON transactions(amount);

            -- جدول الإعدادات
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()

        # تشغيل الهجرة لإعادة تحليل العمليات وتصحيح المحفظة والرصيد
        try:
            from mobile.parser.engine import SMSEngine
            rows = conn.execute("SELECT transaction_id, raw_sms, wallet_id, type FROM transactions").fetchall()
            for row in rows:
                tx_id = row["transaction_id"]
                raw_sms = row["raw_sms"]
                old_wallet = row["wallet_id"]
                old_type = row["type"]
                
                # إعادة التحليل
                tx = SMSEngine.parse(raw_sms)
                
                # توحيد اسم المحفظة
                w_id = tx.wallet_id
                if w_id:
                    w_id = w_id.strip().lower()
                if not w_id or w_id not in ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "instapay", "bank", "unspecified"]:
                    w_id = "unspecified"
                
                # الحفاظ على المحفظة القديمة إذا تم التعرف عليها سابقاً وكانت الجديدة unspecified
                if w_id == "unspecified" and old_wallet:
                    old_wallet_clean = old_wallet.strip().lower()
                    if old_wallet_clean not in ["wallet_001", "unspecified", ""]:
                        w_id = old_wallet_clean
                
                tx_type = tx.type.value if tx.type != TransactionType.UNKNOWN else old_type
                
                # Always update the type if the new parser classified it correctly
                # This ensures ATM_WITHDRAWAL and ATM_DEPOSIT are properly set
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
                    # Use raw_sms as identifier for rows without transaction_id
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
            conn.commit()
            logger.info("🔄 Desktop Cache database successfully migrated and re-parsed.")
        except Exception as e:
            logger.error(f"⚠️ Error running DB migration: {e}")

    # ═════════════════════════════════════════════════════════════════════
    # العمليات (Transactions)
    # ═════════════════════════════════════════════════════════════════════

    def save_transaction(self, tx: Transaction) -> bool:
        """حفظ عملية جديدة قادمة من الموبايل"""
        try:
            w_id = tx.wallet_id
            if w_id:
                w_id = w_id.strip().lower()
            if not w_id or w_id == "unspecified" or w_id not in ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "instapay", "bank"]:
                logger.warning(f"⚠️ Ignoring saving transaction {tx.transaction_id} because wallet/account is unspecified/unknown")
                return False

            self._conn.execute("""
                INSERT OR REPLACE INTO transactions
                    (transaction_id, type, amount, balance_after, counterpart,
                     raw_sms, parsed_at, sms_timestamp, confidence, wallet_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.transaction_id, tx.type.value, tx.amount, tx.balance_after,
                tx.counterpart, tx.raw_sms, tx.parsed_at.isoformat(),
                tx.sms_timestamp.isoformat(), tx.confidence, w_id,
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save transaction to desktop DB: {e}")
            return False

    def get_all_transactions(self,
                             type_filter: str = "ALL",
                             start_date: str = None,
                             end_date: str = None,
                             min_amount: float = None,
                             max_amount: float = None,
                             search_query: str = None,
                             wallet_filter: str = "ALL",
                             limit: int = None,
                             offset: int = None,
                             fee_filter: str = "ALL") -> List[Transaction]:
        """استرجاع العمليات مع دعم الفلاتر والبحث الذكي للـ Dashboard"""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if type_filter and type_filter != "ALL":
            query += " AND type = ?"
            params.append(type_filter)

        if wallet_filter and wallet_filter != "ALL":
            query += " AND wallet_id = ?"
            params.append(wallet_filter)
        else:
            query += " AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''"

        if start_date:
            query += " AND date(sms_timestamp) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(sms_timestamp) <= date(?)"
            params.append(end_date)

        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)

        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)

        if search_query:
            query += " AND (counterpart LIKE ? OR raw_sms LIKE ?)"
            like_query = f"%{search_query}%"
            params.extend([like_query, like_query])

        query += " ORDER BY sms_timestamp DESC"

        use_python_pagination = fee_filter and fee_filter != "ALL"
        db_limit = None if use_python_pagination else limit
        db_offset = None if use_python_pagination else offset

        if db_limit is not None:
            query += " LIMIT ?"
            params.append(db_limit)
            if db_offset is not None:
                query += " OFFSET ?"
                params.append(db_offset)

        rows = self._conn.execute(query, params).fetchall()
        txs = [self._row_to_transaction(r) for r in rows]

        if use_python_pagination:
            if fee_filter == "WITH_FEES":
                txs = [tx for tx in txs if self.calculate_fee(tx) > 0.0]
            elif fee_filter == "WITHOUT_FEES":
                txs = [tx for tx in txs if self.calculate_fee(tx) == 0.0]

            if offset is not None:
                txs = txs[offset:]
            if limit is not None:
                txs = txs[:limit]

        return txs

    def get_transactions_count(self,
                               type_filter: str = "ALL",
                               start_date: str = None,
                               end_date: str = None,
                               min_amount: float = None,
                               max_amount: float = None,
                               search_query: str = None,
                               wallet_filter: str = "ALL",
                               fee_filter: str = "ALL") -> int:
        """الحصول على عدد العمليات المطابقة للفلاتر"""
        if fee_filter and fee_filter != "ALL":
            all_txs = self.get_all_transactions(
                type_filter=type_filter,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search_query=search_query,
                wallet_filter=wallet_filter,
                fee_filter=fee_filter
            )
            return len(all_txs)

        query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
        params = []

        if type_filter and type_filter != "ALL":
            query += " AND type = ?"
            params.append(type_filter)

        if wallet_filter and wallet_filter != "ALL":
            query += " AND wallet_id = ?"
            params.append(wallet_filter)
        else:
            query += " AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''"

        if start_date:
            query += " AND date(sms_timestamp) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(sms_timestamp) <= date(?)"
            params.append(end_date)

        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)

        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)

        if search_query:
            query += " AND (counterpart LIKE ? OR raw_sms LIKE ?)"
            like_query = f"%{search_query}%"
            params.extend([like_query, like_query])

        try:
            row = self._conn.execute(query, params).fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"❌ Error getting transactions count: {e}")
            return 0

    def get_kpi_summary(self, month: str = None) -> Dict[str, float]:
        """إحصائيات (رصيد، دخل، مصاريف) للـ Dashboard"""
        # إذا لم يُحدد شهر، نستخدم الشهر الحالي بالتوقيت المحلي لضمان الدقة
        if month == "ALL":
            date_filter = "IS NOT NULL"
        else:
            date_filter = f"LIKE '{month}%'" if month else ">= date('now', 'localtime', 'start of month')"
        
        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM transactions
            WHERE sms_timestamp {date_filter}
              AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
        """).fetchone()
        
        # حساب رصيد كل محفظة
        wallet_balances = {}
        supported_wallets = ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "instapay", "bank"]
        
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
                    # إذا تم إدخال رصيد ابتدائي يدوي، نعتمد عليه كـ (الرصيد الابتدائي + صافي المعاملات)
                    try:
                        balance = float(initial_bal_str) + net_change
                    except ValueError:
                        balance = 0.0 + net_change
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
                        balance = latest_bal_row["balance_after"]
                    else:
                        # إذا لم يوجد رصيد تلقائي في الرسائل (مثل انستا باي)، نبدأ من 0 + صافي المعاملات
                        balance = 0.0 + net_change
                
                wallet_balances[w_id] = balance
            
        current_balance = sum(wallet_balances.values())

        # حساب إجمالي الرسوم للشهر الحالي
        tx_rows = self._conn.execute(f"""
            SELECT * FROM transactions
            WHERE sms_timestamp {date_filter}
              AND wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
        """).fetchall()
        
        total_fees = 0.0
        for r in tx_rows:
            tx = self._row_to_transaction(r)
            total_fees += self.calculate_fee(tx)

        return {
            "income": row["total_income"],
            "expenses": row["total_expenses"],
            "transactions_count": row["total_transactions"],
            "current_balance": current_balance,
            "wallet_balances": wallet_balances,
            "fees": total_fees
        }

    def calculate_fee(self, tx: Transaction) -> float:
        """
        حساب الرسوم ديناميكياً بناءً على نوع العملية والمحفظة.
        """
        w_id = tx.wallet_id
        if w_id:
            w_id = w_id.strip().lower()
        if not w_id or w_id in ["unspecified", ""]:
            return 0.0

        tx_type = tx.type
        if isinstance(tx_type, str):
            try:
                tx_type = TransactionType(tx_type)
            except ValueError:
                pass

        if tx_type in [TransactionType.RECEIVED, TransactionType.ATM_DEPOSIT]:
            # إيداع / استلام
            dep_fee_str = self.get_setting(f"fee_deposit_{w_id}", "0.0")
            try:
                dep_fee_pct = float(dep_fee_str)
            except ValueError:
                dep_fee_pct = 0.0
            return tx.amount * (dep_fee_pct / 100.0)

        elif tx_type in [TransactionType.SENT, TransactionType.BILL, TransactionType.PURCHASE,
                         TransactionType.TOPUP, TransactionType.ATM_WITHDRAWAL]:
            # سحب / دفوعات / سحب ATM
            wth_fee_str = self.get_setting(f"fee_withdraw_{w_id}", "0.0")
            wth_min_str = self.get_setting(f"fee_withdraw_min_{w_id}", "0.0")
            try:
                wth_fee_pct = float(wth_fee_str)
            except ValueError:
                wth_fee_pct = 0.0
            try:
                wth_min = float(wth_min_str)
            except ValueError:
                wth_min = 0.0

            fee = tx.amount * (wth_fee_pct / 100.0)
            if fee > 0.0 and fee < wth_min:
                fee = wth_min
            return fee

        return 0.0

    def get_available_months(self) -> List[str]:
        """الحصول على قائمة الأشهر الفريدة التي تحتوي على عمليات في قاعدة البيانات"""
        try:
            rows = self._conn.execute(
                "SELECT DISTINCT strftime('%Y-%m', sms_timestamp) as month FROM transactions WHERE month IS NOT NULL AND month != '' ORDER BY month DESC"
            ).fetchall()
            return [r["month"] for r in rows if r["month"]]
        except Exception as e:
            logger.error(f"Error getting available months: {e}")
            return []


    def get_top_contacts(self,
                         start_date: str = None,
                         end_date: str = None,
                         search_query: str = None,
                         sort_by: str = "count",
                         limit: int = 10) -> List[Dict]:
        """استرجاع الأرقام الأكثر تفاعلاً مع إجمالي المبالغ المرسلة والمستلمة"""
        query = """
            SELECT 
                counterpart,
                COUNT(*) as transaction_count,
                SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0.0 END) as total_received,
                SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0.0 END) as total_sent,
                (SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0.0 END) - 
                 SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0.0 END)) as net_flow
            FROM transactions
            WHERE counterpart IS NOT NULL AND counterpart != '' AND counterpart != 'unspecified'
        """
        params = []

        if start_date:
            query += " AND date(sms_timestamp) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(sms_timestamp) <= date(?)"
            params.append(end_date)

        if search_query:
            query += " AND counterpart LIKE ?"
            params.append(f"%{search_query}%")

        query += " GROUP BY counterpart"

        # Apply sorting
        if sort_by == "received":
            query += " ORDER BY total_received DESC"
        elif sort_by == "sent":
            query += " ORDER BY total_sent DESC"
        elif sort_by == "net_flow":
            query += " ORDER BY net_flow DESC"
        else: # default: transaction_count / count
            query += " ORDER BY transaction_count DESC"

        if limit and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        try:
            rows = self._conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error getting top contacts: {e}")
            return []

    def get_transactions_by_counterpart(self, counterpart: str, limit: int = None) -> List[Transaction]:
        """استرجاع العمليات المرتبطة برقم هاتف أو اسم جهة اتصال معينة"""
        if not counterpart:
            return []
        query = "SELECT * FROM transactions WHERE counterpart LIKE ?"
        params = [f"%{counterpart.strip()}%"]
        query += " ORDER BY sms_timestamp DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_transaction(r) for r in rows]

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            transaction_id=row["transaction_id"],
            type=TransactionType(row["type"]),
            amount=row["amount"],
            balance_after=row["balance_after"],
            counterpart=row["counterpart"],
            raw_sms=row["raw_sms"],
            parsed_at=datetime.fromisoformat(row["parsed_at"]),
            sms_timestamp=datetime.fromisoformat(row["sms_timestamp"]),
            confidence=row["confidence"],
            wallet_id=row["wallet_id"],
        )

    def get_setting(self, key: str, default: str) -> str:
        """Get setting value by key."""
        try:
            row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
        return default

    def set_setting(self, key: str, value: str) -> bool:
        """Set setting value by key."""
        try:
            self._conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key} to {value}: {e}")
            return False

    def get_wallet_net_change(self, wallet_id: str) -> float:
        """حساب صافي التغير في الرصيد بناءً على المعاملات المسجلة"""
        try:
            tx_sum = self._conn.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS net_change
                FROM transactions
                WHERE wallet_id = ?
            """, (wallet_id,)).fetchone()
            return tx_sum["net_change"] if tx_sum else 0.0
        except Exception as e:
            logger.error(f"Error getting net change for wallet {wallet_id}: {e}")
            return 0.0

    def clear_database(self) -> bool:
        """مسح جميع العمليات وتصفير قاعدة البيانات"""
        try:
            self._conn.execute("DELETE FROM transactions")
            # امسح الأرصدة الابتدائية اليدوية عند تصفير الحساب لتبدأ من الصفر تماماً
            self._conn.execute("DELETE FROM settings WHERE key LIKE 'initial_balance_%'")
            self._conn.commit()
            logger.info("🗑️ Desktop database cleared successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear desktop database: {e}")
            return False

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
