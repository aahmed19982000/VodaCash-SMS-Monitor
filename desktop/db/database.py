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

    # ═════════════════════════════════════════════════════════════════════
    # العمليات (Transactions)
    # ═════════════════════════════════════════════════════════════════════

    def save_transaction(self, tx: Transaction) -> bool:
        """حفظ عملية جديدة قادمة من الموبايل"""
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO transactions
                    (transaction_id, type, amount, balance_after, counterpart,
                     raw_sms, parsed_at, sms_timestamp, confidence, wallet_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.transaction_id, tx.type.value, tx.amount, tx.balance_after,
                tx.counterpart, tx.raw_sms, tx.parsed_at.isoformat(),
                tx.sms_timestamp.isoformat(), tx.confidence, tx.wallet_id,
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
                             search_query: str = None) -> List[Transaction]:
        """استرجاع العمليات مع دعم الفلاتر والبحث الذكي للـ Dashboard"""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if type_filter and type_filter != "ALL":
            query += " AND type = ?"
            params.append(type_filter)

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
        # إذا لم يُحدد شهر، نستخدم الشهر الحالي
        date_filter = f"LIKE '{month}%'" if month else ">= date('now', 'start of month')"
        
        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type='RECEIVED' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE') THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM transactions
            WHERE sms_timestamp {date_filter}
        """).fetchone()
        
        # آخر رصيد معروف
        balance_row = self._conn.execute("""
            SELECT balance_after FROM transactions 
            WHERE balance_after > 0 
            ORDER BY sms_timestamp DESC LIMIT 1
        """).fetchone()
        current_balance = balance_row["balance_after"] if balance_row else 0.0

        return {
            "income": row["total_income"],
            "expenses": row["total_expenses"],
            "transactions_count": row["total_transactions"],
            "current_balance": current_balance
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
