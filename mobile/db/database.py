# mobile/db/database.py
# ── SQLite Local Cache لتخزين العمليات والرسائل على الموبايل ──────────────

import sqlite3
import threading
import os
import logging
from datetime import datetime
from typing import List, Optional

from shared.models import Transaction, TransactionType, UnclassifiedSMS
from shared.config import MOBILE_DB_PATH

logger = logging.getLogger("VodaCash.DB")


class MobileDatabase:
    """
    قاعدة بيانات SQLite محلية للموبايل.

    الجداول:
    ──────────────────────────────────────────────────
    1. wallets        → المحافظ المسجلة (دعم عدة أرقام)
    2. transactions   → العمليات المصنفة (إرسال، استلام، فاتورة، إلخ)
    3. unclassified   → الرسائل غير المصنفة للمراجعة اليدوية
    4. sync_log       → سجل المزامنة مع سطح المكتب
    5. balance_history → تاريخ تغيرات الرصيد
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """Singleton — نسخة واحدة فقط من قاعدة البيانات."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        self._db_path = db_path or MOBILE_DB_PATH
        self._local = threading.local()
        self._ensure_dir()
        self._create_tables()
        self._initialized = True
        logger.info(f"✅ Database initialized: {self._db_path}")

    # ═════════════════════════════════════════════════════════════════════
    # إدارة الاتصال (Thread-Safe)
    # ═════════════════════════════════════════════════════════════════════

    def _ensure_dir(self):
        """إنشاء مجلد قاعدة البيانات إذا لم يكن موجوداً."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

    @property
    def _conn(self) -> sqlite3.Connection:
        """اتصال خاص بكل Thread."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    # ═════════════════════════════════════════════════════════════════════
    # إنشاء الجداول
    # ═════════════════════════════════════════════════════════════════════

    def _create_tables(self):
        conn = self._conn
        conn.executescript("""
            -- ── جدول المحافظ (Wallet Selector) ──────────────────────────
            CREATE TABLE IF NOT EXISTS wallets (
                wallet_id       TEXT PRIMARY KEY,
                phone_number    TEXT    NOT NULL UNIQUE,
                label           TEXT    DEFAULT '',
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT    DEFAULT (datetime('now'))
            );

            -- ── جدول العمليات المصنفة ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id  TEXT PRIMARY KEY,
                type            TEXT    NOT NULL DEFAULT 'UNKNOWN',
                amount          REAL    NOT NULL DEFAULT 0.0,
                balance_after   REAL    NOT NULL DEFAULT 0.0,
                counterpart     TEXT    DEFAULT '',
                raw_sms         TEXT    NOT NULL,
                parsed_at       TEXT    NOT NULL,
                sms_timestamp   TEXT    NOT NULL,
                confidence      REAL    NOT NULL DEFAULT 0.0,
                wallet_id       TEXT    DEFAULT 'wallet_001',
                synced          INTEGER DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now'))
            );

            -- ── جدول الرسائل غير المصنفة ────────────────────────────────
            CREATE TABLE IF NOT EXISTS unclassified (
                id              TEXT PRIMARY KEY,
                raw_sms         TEXT    NOT NULL,
                sender          TEXT    DEFAULT '',
                received_at     TEXT    NOT NULL,
                confidence      REAL    DEFAULT 0.0,
                reviewed        INTEGER DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now'))
            );

            -- ── سجل المزامنة ────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS sync_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                synced_at       TEXT    NOT NULL,
                tx_count        INTEGER DEFAULT 0,
                status          TEXT    DEFAULT 'SUCCESS',
                details         TEXT    DEFAULT ''
            );

            -- ── تاريخ الرصيد ────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS balance_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                balance         REAL    NOT NULL,
                wallet_id       TEXT    DEFAULT 'wallet_001',
                recorded_at     TEXT    DEFAULT (datetime('now')),
                source_tx_id    TEXT    DEFAULT '',
                FOREIGN KEY (source_tx_id) REFERENCES transactions(transaction_id)
            );

            -- ── الفهارس ──────────────────────────────────────────────────
            CREATE INDEX IF NOT EXISTS idx_tx_type       ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_tx_synced     ON transactions(synced);
            CREATE INDEX IF NOT EXISTS idx_tx_timestamp  ON transactions(sms_timestamp);
            CREATE INDEX IF NOT EXISTS idx_tx_wallet     ON transactions(wallet_id);
            CREATE INDEX IF NOT EXISTS idx_balance_wallet ON balance_history(wallet_id);
        """)
        conn.commit()

    # ═════════════════════════════════════════════════════════════════════
    # العمليات المصنفة (Transactions)
    # ═════════════════════════════════════════════════════════════════════

    def save_transaction(self, tx: Transaction) -> bool:
        """حفظ عملية جديدة + تسجيل الرصيد."""
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO transactions
                    (transaction_id, type, amount, balance_after, counterpart,
                     raw_sms, parsed_at, sms_timestamp, confidence, wallet_id, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                tx.transaction_id, tx.type.value, tx.amount, tx.balance_after,
                tx.counterpart, tx.raw_sms, tx.parsed_at.isoformat(),
                tx.sms_timestamp.isoformat(), tx.confidence, tx.wallet_id,
            ))

            # تسجيل الرصيد إذا كان موجوداً
            if tx.balance_after > 0:
                self._conn.execute("""
                    INSERT INTO balance_history (balance, wallet_id, source_tx_id)
                    VALUES (?, ?, ?)
                """, (tx.balance_after, tx.wallet_id, tx.transaction_id))

            self._conn.commit()
            logger.info(f"💾 Saved: {tx.type.value} — {tx.amount} EGP")
            return True
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            self._conn.rollback()
            return False

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """استرجاع عملية بالـ ID."""
        row = self._conn.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)
        ).fetchone()
        return self._row_to_transaction(row) if row else None

    def get_recent_transactions(self, limit: int = 50) -> List[Transaction]:
        """آخر N عملية مرتبة بالأحدث."""
        rows = self._conn.execute(
            "SELECT * FROM transactions ORDER BY sms_timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [self._row_to_transaction(r) for r in rows]

    def get_unsynced_transactions(self) -> List[Transaction]:
        """العمليات التي لم تُرسل بعد لسطح المكتب."""
        rows = self._conn.execute(
            "SELECT * FROM transactions WHERE synced = 0 ORDER BY sms_timestamp ASC"
        ).fetchall()
        return [self._row_to_transaction(r) for r in rows]

    def mark_synced(self, tx_ids: List[str]):
        """تحديث حالة المزامنة بعد الإرسال الناجح."""
        placeholders = ",".join("?" * len(tx_ids))
        self._conn.execute(
            f"UPDATE transactions SET synced = 1 WHERE transaction_id IN ({placeholders})",
            tx_ids
        )
        self._conn.commit()

    # ═════════════════════════════════════════════════════════════════════
    # الرسائل غير المصنفة
    # ═════════════════════════════════════════════════════════════════════

    def save_unclassified(self, sms: UnclassifiedSMS) -> bool:
        """حفظ رسالة غير مصنفة."""
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO unclassified
                    (id, raw_sms, sender, received_at, confidence, reviewed)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                sms.id, sms.raw_sms, sms.sender,
                sms.received_at.isoformat(), sms.confidence,
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Save unclassified failed: {e}")
            return False

    def get_unreviewed(self) -> List[dict]:
        """الرسائل غير المراجعة."""
        rows = self._conn.execute(
            "SELECT * FROM unclassified WHERE reviewed = 0 ORDER BY received_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def classify_manually(self, sms_id: str, tx_type: str, amount: float,
                          counterpart: str = "", wallet_id: str = "wallet_001") -> bool:
        """تصنيف رسالة يدوياً — نقلها من unclassified إلى transactions."""
        try:
            row = self._conn.execute(
                "SELECT * FROM unclassified WHERE id = ?", (sms_id,)
            ).fetchone()
            if not row:
                return False

            import uuid
            tx = Transaction(
                transaction_id=str(uuid.uuid4()),
                type=TransactionType(tx_type),
                amount=amount,
                counterpart=counterpart,
                raw_sms=row["raw_sms"],
                sms_timestamp=datetime.fromisoformat(row["received_at"]),
                confidence=1.0,  # تصنيف يدوي = ثقة كاملة
                wallet_id=wallet_id,
            )
            self.save_transaction(tx)

            # تحديث حالة المراجعة
            self._conn.execute(
                "UPDATE unclassified SET reviewed = 1 WHERE id = ?", (sms_id,)
            )
            self._conn.commit()
            logger.info(f"✏️ Manually classified: {tx_type} — {amount} EGP")
            return True
        except Exception as e:
            logger.error(f"❌ Manual classify failed: {e}")
            return False

    def dismiss_unclassified(self, sms_id: str) -> bool:
        """تجاهل رسالة غير مصنفة."""
        self._conn.execute(
            "UPDATE unclassified SET reviewed = 1 WHERE id = ?", (sms_id,)
        )
        self._conn.commit()
        return True

    # ═════════════════════════════════════════════════════════════════════
    # الرصيد والإحصائيات
    # ═════════════════════════════════════════════════════════════════════

    def get_current_balance(self, wallet_id: str = "wallet_001") -> float:
        """آخر رصيد مسجل."""
        row = self._conn.execute(
            "SELECT balance FROM balance_history WHERE wallet_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (wallet_id,)
        ).fetchone()
        return row["balance"] if row else 0.0

    def get_daily_summary(self, date: str = None) -> dict:
        """ملخص اليوم (أو تاريخ محدد)."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        row = self._conn.execute("""
            SELECT
                COUNT(*)                                           AS total_count,
                COALESCE(SUM(CASE WHEN type='RECEIVED' THEN amount ELSE 0 END), 0) AS total_received,
                COALESCE(SUM(CASE WHEN type='SENT'     THEN amount ELSE 0 END), 0) AS total_sent,
                COALESCE(SUM(CASE WHEN type='BILL'     THEN amount ELSE 0 END), 0) AS total_bills,
                COALESCE(SUM(CASE WHEN type='TOPUP'    THEN amount ELSE 0 END), 0) AS total_topup
            FROM transactions
            WHERE DATE(sms_timestamp) = ?
        """, (date,)).fetchone()

        return dict(row) if row else {}

    def get_stats(self) -> dict:
        """إحصائيات عامة."""
        row = self._conn.execute("""
            SELECT
                COUNT(*)                          AS total,
                SUM(CASE WHEN synced=1 THEN 1 ELSE 0 END) AS synced,
                SUM(CASE WHEN synced=0 THEN 1 ELSE 0 END) AS unsynced
            FROM transactions
        """).fetchone()
        return dict(row) if row else {}

    # ═════════════════════════════════════════════════════════════════════
    # سجل المزامنة
    # ═════════════════════════════════════════════════════════════════════

    def log_sync(self, tx_count: int, status: str = "SUCCESS", details: str = ""):
        """تسجيل عملية مزامنة."""
        self._conn.execute("""
            INSERT INTO sync_log (synced_at, tx_count, status, details)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), tx_count, status, details))
        self._conn.commit()

    # ═════════════════════════════════════════════════════════════════════
    # إدارة المحافظ (Wallet Selector)
    # ═════════════════════════════════════════════════════════════════════

    def add_wallet(self, wallet_id: str, phone_number: str, label: str = "") -> bool:
        """إضافة محفظة جديدة."""
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO wallets (wallet_id, phone_number, label) VALUES (?, ?, ?)",
                (wallet_id, phone_number, label)
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Add wallet failed: {e}")
            return False

    def get_wallets(self) -> List[dict]:
        """كل المحافظ المسجلة."""
        rows = self._conn.execute(
            "SELECT * FROM wallets ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_active_wallet(self) -> Optional[dict]:
        """المحفظة النشطة حالياً."""
        row = self._conn.execute(
            "SELECT * FROM wallets WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def set_active_wallet(self, wallet_id: str):
        """تغيير المحفظة النشطة."""
        self._conn.execute("UPDATE wallets SET is_active = 0")
        self._conn.execute(
            "UPDATE wallets SET is_active = 1 WHERE wallet_id = ?", (wallet_id,)
        )
        self._conn.commit()

    # ═════════════════════════════════════════════════════════════════════
    # أدوات مساعدة
    # ═════════════════════════════════════════════════════════════════════

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        """تحويل صف من قاعدة البيانات إلى كائن Transaction."""
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

    def close(self):
        """إغلاق الاتصال للـ Thread الحالي."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
