# mobile/db/database.py
import sqlite3
import threading
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from shared.models import Transaction, TransactionType, UnclassifiedSMS

logger = logging.getLogger("VodaCash.MobileDB")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOBILE_DB_PATH = os.path.join(BASE_DIR, "mobile", "db", "mobile_cache.db")

class MobileDatabase:
    """قاعدة البيانات المحلية للموبايل لتخزين العمليات (Queue) والرسائل والإعدادات."""
    
    def __init__(self, db_path=MOBILE_DB_PATH):
        self._db_path = db_path
        self._local = threading.local()
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._create_tables()
        logger.info(f"✅ Mobile Database initialized at: {self._db_path}")

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id  TEXT PRIMARY KEY,
                type            TEXT NOT NULL,
                amount          REAL NOT NULL,
                balance_after   REAL NOT NULL,
                counterpart     TEXT DEFAULT '',
                raw_sms         TEXT NOT NULL,
                parsed_at       TEXT NOT NULL,
                sms_timestamp   TEXT NOT NULL,
                confidence      REAL NOT NULL,
                wallet_id       TEXT DEFAULT '',
                is_synced       INTEGER DEFAULT 0, -- مزامنة مع الديسكتوب
                is_synced_server INTEGER DEFAULT 0 -- مزامنة مباشرة مع السيرفر
            );

            CREATE TABLE IF NOT EXISTS unclassified_sms (
                id            TEXT PRIMARY KEY,
                raw_sms       TEXT NOT NULL,
                sender        TEXT NOT NULL,
                received_at   TEXT NOT NULL,
                confidence    REAL NOT NULL,
                reviewed      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT DEFAULT (datetime('now')),
                count       INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._conn.commit()

    # ── إدارة الإعدادات ──
    def get_setting(self, key: str, default: str = "") -> str:
        try:
            row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: str):
        try:
            self._conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")

    # ── حفظ المعاملات والرسائل غير المصنفة ──
    def save_transaction(self, tx: Transaction) -> bool:
        try:
            # التحقق مما إذا كانت المعاملة موجودة مسبقاً
            cursor = self._conn.execute("SELECT transaction_id FROM transactions WHERE transaction_id = ?", (tx.transaction_id,))
            if cursor.fetchone():
                return False

            self._conn.execute("""
                INSERT INTO transactions (
                    transaction_id, type, amount, balance_after, counterpart,
                    raw_sms, parsed_at, sms_timestamp, confidence, wallet_id,
                    is_synced, is_synced_server
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                tx.transaction_id, tx.type.value, tx.amount, tx.balance_after, tx.counterpart,
                tx.raw_sms, tx.parsed_at.isoformat(), tx.sms_timestamp.isoformat(), tx.confidence, tx.wallet_id
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            return False

    def save_unclassified(self, sms: UnclassifiedSMS) -> bool:
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO unclassified_sms (id, raw_sms, sender, received_at, confidence, reviewed)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                sms.id, sms.raw_sms, sms.sender, sms.received_at.isoformat(), sms.confidence
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving unclassified SMS: {e}")
            return False

    # ── استرجاع ومزامنة المعاملات ──
    def get_unsynced_transactions(self) -> List[Transaction]:
        """المعاملات غير المزامنة مع تطبيق الديسكتوب"""
        try:
            rows = self._conn.execute("SELECT * FROM transactions WHERE is_synced = 0").fetchall()
            return [self._row_to_transaction(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting unsynced transactions: {e}")
            return []

    def get_unsynced_server_transactions(self) -> List[Transaction]:
        """المعاملات غير المزامنة مع السيرفر المركزي"""
        try:
            rows = self._conn.execute("SELECT * FROM transactions WHERE is_synced_server = 0").fetchall()
            return [self._row_to_transaction(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting unsynced server transactions: {e}")
            return []

    def mark_synced(self, ids: List[str]):
        """تحديد المعاملات كتمت مزامنتها مع الديسكتوب"""
        if not ids:
            return
        try:
            placeholders = ",".join("?" for _ in ids)
            self._conn.execute(f"UPDATE transactions SET is_synced = 1 WHERE transaction_id IN ({placeholders})", ids)
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error marking synced: {e}")

    def mark_server_synced(self, ids: List[str]):
        """تحديد المعاملات كتمت مزامنتها مع السيرفر"""
        if not ids:
            return
        try:
            placeholders = ",".join("?" for _ in ids)
            self._conn.execute(f"UPDATE transactions SET is_synced_server = 1 WHERE transaction_id IN ({placeholders})", ids)
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error marking server synced: {e}")

    def log_sync(self, count: int):
        try:
            self._conn.execute("INSERT INTO sync_logs (count) VALUES (?)", (count,))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error logging sync: {e}")

    # ── الاستعلامات والإحصائيات ──
    def get_recent_transactions(self, limit: int = 5) -> List[Transaction]:
        try:
            rows = self._conn.execute("SELECT * FROM transactions ORDER BY sms_timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [self._row_to_transaction(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []

    def get_current_balance(self) -> float:
        try:
            row = self._conn.execute("SELECT balance_after FROM transactions WHERE balance_after >= 0 ORDER BY sms_timestamp DESC LIMIT 1").fetchone()
            return row["balance_after"] if row else 0.0
        except Exception as e:
            logger.error(f"Error getting current balance: {e}")
            return 0.0

    def get_stats(self) -> Dict[str, Any]:
        try:
            total_tx = self._conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            unsynced_desktop = self._conn.execute("SELECT COUNT(*) FROM transactions WHERE is_synced = 0").fetchone()[0]
            unsynced_server = self._conn.execute("SELECT COUNT(*) FROM transactions WHERE is_synced_server = 0").fetchone()[0]
            unclassified = self._conn.execute("SELECT COUNT(*) FROM unclassified_sms").fetchone()[0]
            return {
                "total_transactions": total_tx,
                "unsynced_transactions": unsynced_desktop,
                "unsynced_server_transactions": unsynced_server,
                "unclassified_count": unclassified
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_transactions": 0,
                "unsynced_transactions": 0,
                "unsynced_server_transactions": 0,
                "unclassified_count": 0
            }

    def get_daily_summary(self) -> Dict[str, float]:
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            rows = self._conn.execute("""
                SELECT type, SUM(amount) as total FROM transactions 
                WHERE sms_timestamp LIKE ? GROUP BY type
            """, (f"{today_str}%",)).fetchall()
            
            summary = {"RECEIVED": 0.0, "SENT": 0.0}
            for r in rows:
                if r["type"] in summary:
                    summary[r["type"]] = r["total"]
            return summary
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {"RECEIVED": 0.0, "SENT": 0.0}

    # ── التوافق مع الكود القديم (Offline Queue) ──
    def enqueue(self, payload: str):
        try:
            self._conn.execute("INSERT INTO offline_queue (payload) VALUES (?)", (payload,))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error enqueuing: {e}")

    def get_all(self):
        try:
            rows = self._conn.execute("SELECT id, payload FROM offline_queue ORDER BY id ASC").fetchall()
            return [{"id": r["id"], "payload": r["payload"]} for r in rows]
        except Exception as e:
            logger.error(f"Error getting all queued: {e}")
            return []

    def remove(self, record_id: int):
        try:
            self._conn.execute("DELETE FROM offline_queue WHERE id = ?", (record_id,))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Error removing queued item: {e}")

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def _row_to_transaction(self, r: sqlite3.Row) -> Transaction:
        return Transaction(
            transaction_id=r["transaction_id"],
            type=TransactionType(r["type"]),
            amount=r["amount"],
            balance_after=r["balance_after"],
            counterpart=r["counterpart"],
            raw_sms=r["raw_sms"],
            parsed_at=datetime.fromisoformat(r["parsed_at"]),
            sms_timestamp=datetime.fromisoformat(r["sms_timestamp"]),
            confidence=r["confidence"],
            wallet_id=r["wallet_id"]
        )
