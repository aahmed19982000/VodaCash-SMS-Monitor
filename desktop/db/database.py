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
                
                conn.execute("""
                    UPDATE transactions
                    SET wallet_id = ?, balance_after = ?, type = ?
                    WHERE transaction_id = ?
                """, (w_id, tx.balance_after, tx_type, tx_id))
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
                             wallet_filter: str = "ALL") -> List[Transaction]:
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

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_transaction(r) for r in rows]

    def get_kpi_summary(self, month: str = None) -> Dict[str, float]:
        """إحصائيات (رصيد، دخل، مصاريف) للـ Dashboard"""
        # إذا لم يُحدد شهر، نستخدم الشهر الحالي بالتوقيت المحلي لضمان الدقة
        date_filter = f"LIKE '{month}%'" if month else ">= date('now', 'localtime', 'start of month')"
        
        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type='RECEIVED' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP') THEN amount ELSE 0 END), 0) AS total_expenses,
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
                        COALESCE(SUM(CASE WHEN type='RECEIVED' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP') THEN amount ELSE 0 END), 0) AS net_change
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

        return {
            "income": row["total_income"],
            "expenses": row["total_expenses"],
            "transactions_count": row["total_transactions"],
            "current_balance": current_balance,
            "wallet_balances": wallet_balances
        }

    def get_transactions_by_counterpart(self, counterpart: str) -> List[Transaction]:
        """استرجاع العمليات المرتبطة برقم هاتف أو اسم جهة اتصال معينة"""
        if not counterpart:
            return []
        query = "SELECT * FROM transactions WHERE counterpart LIKE ? ORDER BY sms_timestamp DESC"
        like_query = f"%{counterpart.strip()}%"
        rows = self._conn.execute(query, (like_query,)).fetchall()
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
                    COALESCE(SUM(CASE WHEN type='RECEIVED' THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP') THEN amount ELSE 0 END), 0) AS net_change
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
