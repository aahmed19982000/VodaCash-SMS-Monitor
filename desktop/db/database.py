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
        
        # آخر رصيد معروف لكل محفظة باستخدام ROW_NUMBER لتجنب تكرار العمليات في نفس التوقيت
        wallet_balances = {}
        balance_rows = self._conn.execute("""
            SELECT wallet_id, balance_after
            FROM (
                SELECT wallet_id, balance_after,
                       ROW_NUMBER() OVER (
                           PARTITION BY wallet_id 
                           ORDER BY sms_timestamp DESC, received_at DESC, transaction_id DESC
                       ) as rn
                FROM transactions
                WHERE balance_after >= 0 
                  AND wallet_id IS NOT NULL 
                  AND wallet_id != 'unspecified' 
                  AND wallet_id != ''
            )
            WHERE rn = 1
        """).fetchall()
        
        for brow in balance_rows:
            w_id = brow["wallet_id"]
            if w_id:
                w_id = w_id.strip().lower()
            if not w_id or w_id not in ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "instapay", "bank"]:
                continue
            wallet_balances[w_id] = brow["balance_after"]
            
        current_balance = sum(wallet_balances.values())

        return {
            "income": row["total_income"],
            "expenses": row["total_expenses"],
            "transactions_count": row["total_transactions"],
            "current_balance": current_balance,
            "wallet_balances": wallet_balances
        }

    # ═════════════════════════════════════════════════════════════════════
    # أدوات
    # ═════════════════════════════════════════════════════════════════════

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

    def clear_database(self) -> bool:
        """مسح جميع العمليات وتصفير قاعدة البيانات"""
        try:
            self._conn.execute("DELETE FROM transactions")
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
