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
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
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
                received_at     TEXT    DEFAULT (datetime('now')),
                is_synced       INTEGER DEFAULT 0
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

            -- سجل حركات النقدية
            CREATE TABLE IF NOT EXISTS cash_ledger (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                type         TEXT    NOT NULL,
                amount       REAL    NOT NULL,
                description  TEXT    DEFAULT '',
                source_tx_id TEXT    DEFAULT '',
                created_at   TEXT    DEFAULT (datetime('now'))
            );

            -- الرسائل غير المصنفة
            CREATE TABLE IF NOT EXISTS unclassified_sms (
                id            TEXT PRIMARY KEY,
                raw_sms       TEXT NOT NULL,
                sender        TEXT NOT NULL,
                received_at   TEXT NOT NULL,
                confidence    REAL NOT NULL,
                reviewed      INTEGER DEFAULT 0
            );

            -- جدول الأنماط المخزنة مؤقتاً من السيرفر
            CREATE TABLE IF NOT EXISTS cached_patterns (
                pattern_id    TEXT PRIMARY KEY,
                type          TEXT NOT NULL,
                regex_pattern TEXT NOT NULL,
                groups_json   TEXT NOT NULL,
                updated_at    TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()

        # هجرة: إضافة عمود is_synced إذا لم يكن موجوداً
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
            if "is_synced" not in cols:
                conn.execute("ALTER TABLE transactions ADD COLUMN is_synced INTEGER DEFAULT 0")
                conn.commit()
                logger.info("✅ Added is_synced column to transactions table")
        except Exception as e:
            logger.warning(f"is_synced migration warning: {e}")

        # هجرة: إضافة عمود profit_status إذا لم يكن موجوداً
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
            if "profit_status" not in cols:
                conn.execute("ALTER TABLE transactions ADD COLUMN profit_status TEXT DEFAULT 'UNSET'")
                conn.commit()
                logger.info("✅ Added profit_status column to transactions table")
        except Exception as e:
            logger.warning(f"profit_status migration warning: {e}")

        # هجرة: تحويل محفظة instapay إلى bank لتوحيد الحسابات
        try:
            conn.execute("UPDATE transactions SET wallet_id = 'bank' WHERE wallet_id = 'instapay'")
            conn.commit()
            logger.info("✅ Migrated instapay transactions to bank wallet")
        except Exception as e:
            logger.warning(f"instapay to bank migration warning: {e}")

        # تشغيل الهجرة لإعادة تحليل العمليات وتصحيح المحفظة والرصيد
        try:
            # Check if this migration was already completed to prevent slow startup
            try:
                cur = conn.execute("SELECT value FROM settings WHERE key = 'migration_reparse_v3'")
                row = cur.fetchone()
                if row and row[0] == "done":
                    logger.info("⚡ Reparsing migration already completed. Skipping.")
                    return
            except Exception as se:
                logger.debug(f"Could not check migration setting (expected on fresh DB): {se}")

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
                amount = tx.amount
                
                # Always update the type if the new parser classified it correctly
                # This ensures ATM_WITHDRAWAL and ATM_DEPOSIT are properly set
                balance_after = tx.balance_after if tx.balance_after >= 0 else None
                
                if tx_id is not None:
                    if balance_after is not None:
                        conn.execute(
                            "UPDATE transactions SET wallet_id=?, type=?, amount=?, balance_after=? WHERE transaction_id=?",
                            (w_id, tx_type, amount, balance_after, tx_id)
                        )
                    else:
                        conn.execute(
                            "UPDATE transactions SET wallet_id=?, type=?, amount=? WHERE transaction_id=?",
                            (w_id, tx_type, amount, tx_id)
                        )
                else:
                    # Use raw_sms as identifier for rows without transaction_id
                    if balance_after is not None:
                        conn.execute(
                            "UPDATE transactions SET wallet_id=?, type=?, amount=?, balance_after=? WHERE transaction_id IS NULL AND raw_sms=?",
                            (w_id, tx_type, amount, balance_after, raw_sms)
                        )
                    else:
                        conn.execute(
                            "UPDATE transactions SET wallet_id=?, type=?, amount=? WHERE transaction_id IS NULL AND raw_sms=?",
                            (w_id, tx_type, amount, raw_sms)
                        )
            
            # Mark migration as done
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('migration_reparse_v3', 'done')")
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

            # Check if transaction already exists to preserve its profit_status and details
            if tx.transaction_id:
                cursor = self._conn.execute(
                    "SELECT profit_status FROM transactions WHERE transaction_id = ?",
                    (tx.transaction_id,)
                )
                row = cursor.fetchone()
                if row is not None:
                    logger.info(f"ℹ️ Transaction {tx.transaction_id} already exists in database (status: {row[0]}). Skipping insert.")
                    return False

            self._conn.execute("""
                INSERT INTO transactions
                    (transaction_id, type, amount, balance_after, counterpart,
                     raw_sms, parsed_at, sms_timestamp, confidence, wallet_id, is_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
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

    def get_unsynced_transactions(self) -> List[Transaction]:
        """استرجاع جميع المعاملات غير المزامنة مع السيرفر لرفعها لاحقاً"""
        try:
            rows = self._conn.execute(
                "SELECT * FROM transactions WHERE is_synced = 0"
            ).fetchall()
            return [self._row_to_transaction(r) for r in rows]
        except Exception as e:
            logger.error(f"❌ Failed to get unsynced transactions: {e}")
            return []

    def mark_transaction_synced(self, tx_id: str) -> bool:
        """تحديث حالة المعاملة لتصبح مزامنة"""
        try:
            self._conn.execute(
                "UPDATE transactions SET is_synced = 1 WHERE transaction_id = ?",
                (tx_id,)
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to mark transaction synced: {e}")
            return False

    def transaction_exists(self, tx_id: str, raw_sms: str = None) -> bool:
        """التحقق من وجود المعاملة مسبقاً في قاعدة البيانات لتفادي تكرار معالجتها"""
        try:
            if tx_id:
                row = self._conn.execute(
                    "SELECT 1 FROM transactions WHERE transaction_id = ?",
                    (tx_id,)
                ).fetchone()
                if row is not None:
                    return True
            if raw_sms:
                row = self._conn.execute(
                    "SELECT 1 FROM transactions WHERE raw_sms = ?",
                    (raw_sms,)
                ).fetchone()
                return row is not None
            return False
        except Exception as e:
            logger.error(f"❌ Error checking if transaction exists: {e}")
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
                             fee_filter: str = "ALL",
                             profit_status_filter: str = "ALL") -> List[Transaction]:
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
            track_instapay = self.get_setting("track_instapay", "true") == "true"
            if not track_instapay:
                query += " AND wallet_id != 'bank'"

        if profit_status_filter and profit_status_filter != "ALL":
            query += " AND COALESCE(profit_status, 'UNSET') = ?"
            params.append(profit_status_filter)

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
                               fee_filter: str = "ALL",
                               profit_status_filter: str = "ALL") -> int:
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
                fee_filter=fee_filter,
                profit_status_filter=profit_status_filter
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

        if profit_status_filter and profit_status_filter != "ALL":
            query += " AND COALESCE(profit_status, 'UNSET') = ?"
            params.append(profit_status_filter)

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

    def get_kpi_summary(self, month: str = None, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """إحصائيات (رصيد، دخل، مصاريف) للـ Dashboard"""
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
        
        track_instapay = self.get_setting("track_instapay", "true") == "true"
        wallet_filter = ""
        if not track_instapay:
            wallet_filter = "AND wallet_id != 'bank'"

        row = self._conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS total_expenses,
                COUNT(*) AS total_transactions
            FROM transactions
            WHERE wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
              {wallet_filter}
              {date_filter}
        """, filter_params).fetchone()
        
        # حساب رصيد كل محفظة
        wallet_balances = {}
        supported_wallets = ["vodafone_cash", "orange_cash", "etisalat_cash", "we_pay", "bank"]
        if not track_instapay:
            supported_wallets.remove("bank")
        
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

        # حساب إجمالي الرسوم للشهر الحالي
        tx_rows = self._conn.execute(f"""
            SELECT * FROM transactions
            WHERE wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
              {wallet_filter}
              {date_filter}
        """, filter_params).fetchall()
        
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

        # RECEIVED represents Customer Withdrawal (سحب للعميل). We charge the withdraw fee.
        if tx_type == TransactionType.RECEIVED:
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

        # SENT, BILL, PURCHASE, TOPUP represents Customer Deposit (إيداع للعميل). We charge the deposit fee.
        elif tx_type in [TransactionType.SENT, TransactionType.BILL, TransactionType.PURCHASE, TransactionType.TOPUP]:
            dep_fee_str = self.get_setting(f"fee_deposit_{w_id}", "0.0")
            wth_min_str = self.get_setting(f"fee_withdraw_min_{w_id}", "0.0")
            try:
                dep_fee_pct = float(dep_fee_str)
            except ValueError:
                dep_fee_pct = 0.0
            try:
                wth_min = float(wth_min_str)
            except ValueError:
                wth_min = 0.0

            fee = tx.amount * (dep_fee_pct / 100.0)
            if fee > 0.0 and fee < wth_min:
                fee = wth_min
            return fee

        # ATM_WITHDRAWAL and ATM_DEPOSIT are internal movements and do not generate customer profit
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
        keys = row.keys() if hasattr(row, "keys") else []
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
            profit_status=row["profit_status"] if "profit_status" in keys else "UNSET",
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
            if key == "initial_cash_balance":
                self._conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("initial_cash_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key} to {value}: {e}")
            return False

    def get_wallet_net_change(self, wallet_id: str) -> float:
        """حساب صافي التغير في الرصيد بناءً على المعاملات المسجلة دون طرح الأرباح"""
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
            self._conn.execute("DELETE FROM cash_ledger")
            # امسح الأرصدة الابتدائية اليدوية عند تصفير الحساب لتبدأ من الصفر تماماً
            self._conn.execute("DELETE FROM settings WHERE key LIKE 'initial_balance_%'")
            self._conn.commit()
            logger.info("🗑️ Desktop database cleared successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear desktop database: {e}")
            return False

    def get_transaction_profit_status(self, tx_id: str) -> str:
        """
        الحصول على حالة الربح لمعاملة معينة.
        """
        try:
            row = self._conn.execute(
                "SELECT profit_status FROM transactions WHERE transaction_id=?",
                (tx_id,)
            ).fetchone()
            if row:
                return row["profit_status"] or "UNSET"
            return "UNSET"
        except Exception as e:
            logger.error(f"❌ Error getting transaction profit status: {e}")
            return "UNSET"

    def mark_profit_status(self, tx_id: str, raw_sms: str, status: str) -> bool:
        """
        تحديث حالة الربح لعملية معينة ومزامنة حركة الخزينة (النقدية) تلقائياً.
        status: 'IN_WALLET' | 'CASH' | 'NONE' | 'UNSET'
        """
        valid = {"IN_WALLET", "CASH", "NONE", "UNSET"}
        if status not in valid:
            logger.error(f"Invalid profit_status: {status}")
            return False
        try:
            # 1. جلب بيانات العملية والرسوم
            if tx_id:
                row = self._conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
            else:
                row = self._conn.execute("SELECT * FROM transactions WHERE transaction_id IS NULL AND raw_sms = ?", (raw_sms,)).fetchone()
            
            if not row:
                logger.error("Transaction not found for marking profit status")
                return False
                
            tx = self._row_to_transaction(row)
            fee = self.calculate_fee(tx)
            
            # 2. تحديث حالة الأرباح
            if tx_id is not None:
                self._conn.execute(
                    "UPDATE transactions SET profit_status=? WHERE transaction_id=?",
                    (status, tx_id)
                )
            else:
                self._conn.execute(
                    "UPDATE transactions SET profit_status=? WHERE transaction_id IS NULL AND raw_sms=?",
                    (status, raw_sms)
                )
                
            # 3. مزامنة سجل النقدية تلقائياً لمنع التكرار أو الفقدان
            id_for_ledger = str(tx_id) if tx_id else raw_sms
            self._conn.execute("DELETE FROM cash_ledger WHERE source_tx_id = ?", (id_for_ledger,))
            
            if status == "CASH" and fee > 0.0:
                tx_type_str = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
                tx_amount_val = tx.amount if tx.amount is not None else 0.0
                desc = f"ربح من {tx_type_str} — {tx.wallet_id or ''} — {tx_amount_val:,.2f} EGP"
                self._conn.execute(
                    "INSERT INTO cash_ledger (type, amount, description, source_tx_id) VALUES ('PROFIT_IN', ?, ?, ?)",
                    (fee, desc, id_for_ledger)
                )
                
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error marking profit status: {e}")
            return False

    def get_profit_summary(self) -> dict:
        """
        إجمالي الأرباح مقسمة حسب الحالة:
        - in_wallet: أرباح لا تزال في المحفظة
        - cash:      أرباح استُلمت نقداً
        - unset:     أرباح لم يُحدد وضعها بعد
        """
        try:
            rows = self._conn.execute("""
                SELECT *
                FROM transactions
                WHERE wallet_id IS NOT NULL AND wallet_id != 'unspecified' AND wallet_id != ''
            """).fetchall()

            in_wallet = 0.0
            cash_taken = 0.0
            unset_total = 0.0

            for r in rows:
                tx = self._row_to_transaction(r)
                fee = self.calculate_fee(tx)
                if fee <= 0:
                    continue
                ps = r["profit_status"] if "profit_status" in r.keys() else "UNSET"
                if ps == "IN_WALLET":
                    in_wallet += fee
                elif ps == "CASH":
                    cash_taken += fee
                else:  # UNSET or NONE with fee > 0
                    unset_total += fee

            return {
                "in_wallet": in_wallet,
                "cash": cash_taken,
                "unset": unset_total,
                "total": in_wallet + cash_taken + unset_total,
            }
        except Exception as e:
            logger.error(f"❌ Error getting profit summary: {e}")
            return {"in_wallet": 0.0, "cash": 0.0, "unset": 0.0, "total": 0.0}

    # ═════════════════════════════════════════════════════════════════════
    # إدارة النقدية (Cash Ledger)
    # ═════════════════════════════════════════════════════════════════════

    def add_cash_entry(self, entry_type: str, amount: float,
                       description: str = "", source_tx_id: str = "") -> bool:
        """
        إضافة حركة نقدية.
        entry_type: 'CASH_IN' | 'CASH_OUT' | 'PROFIT_IN' | 'EXPENSE'
        """
        valid = {"CASH_IN", "CASH_OUT", "PROFIT_IN", "EXPENSE"}
        if entry_type not in valid:
            logger.error(f"Invalid cash entry type: {entry_type}")
            return False
        try:
            self._conn.execute(
                "INSERT INTO cash_ledger (type, amount, description, source_tx_id) VALUES (?, ?, ?, ?)",
                (entry_type, abs(amount), description, source_tx_id)
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error adding cash entry: {e}")
            return False

    def delete_cash_entry(self, entry_id: int) -> bool:
        """حذف حركة نقدية بالمعرف"""
        try:
            self._conn.execute("DELETE FROM cash_ledger WHERE id=?", (entry_id,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting cash entry: {e}")
            return False

    def get_cash_summary(self) -> dict:
        """
        إجمالي النقدية:
        - total_in:  كل النقد الداخل (CASH_IN + PROFIT_IN + العمليات التلقائية)
        - total_out: كل النقد الخارج (CASH_OUT + EXPENSE + العمليات التلقائية)
        - balance:   الرصيد النقدي المتاح (الافتتاحية + الداخل - الخارج)
        """
        try:
            initial_cash_ts = self.get_setting("initial_cash_timestamp", "1970-01-01 00:00:00")

            # 1. حساب حركات النقدية اليدوية من الخزينة بعد توقيت النقدية الافتتاحية
            row = self._conn.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN type IN ('CASH_IN', 'PROFIT_IN') THEN amount ELSE 0 END), 0) AS total_in,
                    COALESCE(SUM(CASE WHEN type IN ('CASH_OUT', 'EXPENSE')  THEN amount ELSE 0 END), 0) AS total_out
                FROM cash_ledger
                WHERE datetime(created_at, 'localtime') >= datetime(?)
            """, (initial_cash_ts,)).fetchone()
            ledger_in  = row["total_in"]  if row else 0.0
            ledger_out = row["total_out"] if row else 0.0

            # 2. حساب حركات النقدية التلقائية من العمليات بعد توقيت النقدية الافتتاحية
            tx_rows = self._conn.execute("""
                SELECT * FROM transactions
                WHERE wallet_id IS NOT NULL AND wallet_id NOT IN ('unspecified', '', 'bank')
                  AND datetime(sms_timestamp) >= datetime(?)
            """, (initial_cash_ts,)).fetchall()

            tx_in = 0.0
            tx_out = 0.0
            for r in tx_rows:
                t_type = r["type"]
                amount = r["amount"]
                p_status = r["profit_status"] if "profit_status" in r.keys() else "UNSET"

                # حساب العمولة لهذه المعاملة
                tx = self._row_to_transaction(r)
                fee = self.calculate_fee(tx)

                if t_type in ['SENT', 'BILL', 'PURCHASE', 'TOPUP']:
                    tx_in += amount
                elif t_type == 'ATM_WITHDRAWAL':
                    tx_in += amount
                elif t_type == 'RECEIVED':
                    if p_status == "CASH":
                        tx_out += amount
                    elif p_status in ['IN_WALLET', 'UNSET']:
                        tx_out += max(0.0, amount - fee)
                    else:
                        tx_out += amount
                elif t_type == 'ATM_DEPOSIT':
                    tx_out += amount

            # 3. جلب النقدية الافتتاحية من الإعدادات
            initial_cash_str = self.get_setting("initial_cash_balance", "0.0")
            try:
                initial_cash = float(initial_cash_str)
            except ValueError:
                initial_cash = 0.0

            total_in = ledger_in + tx_in
            total_out = ledger_out + tx_out

            return {
                "initial_cash": initial_cash,
                "total_in":  total_in,
                "total_out": total_out,
                "balance":   initial_cash + total_in - total_out,
                "tx_in":     tx_in,
                "tx_out":    tx_out,
                "ledger_in": ledger_in,
                "ledger_out":ledger_out
            }
        except Exception as e:
            logger.error(f"❌ Error getting cash summary: {e}")
            return {
                "initial_cash": 0.0,
                "total_in": 0.0,
                "total_out": 0.0,
                "balance": 0.0,
                "tx_in": 0.0,
                "tx_out": 0.0,
                "ledger_in": 0.0,
                "ledger_out": 0.0
            }

    def get_cash_ledger(self, limit: int = 100, offset: int = 0) -> list:
        """جلب سجل حركات النقدية مرتباً من الأحدث للأقدم"""
        try:
            rows = self._conn.execute(
                "SELECT * FROM cash_ledger ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"❌ Error getting cash ledger: {e}")
            return []

    def get_cash_ledger_count(self) -> int:
        try:
            r = self._conn.execute("SELECT COUNT(*) FROM cash_ledger").fetchone()
            return r[0] if r else 0
        except Exception:
            return 0

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def save_unclassified_sms(self, sms: dict) -> bool:
        """حفظ رسالة واردة غير مصنفة لمراجعتها يدوياً"""
        try:
            from datetime import datetime
            self._conn.execute("""
                INSERT OR REPLACE INTO unclassified_sms
                    (id, raw_sms, sender, received_at, confidence, reviewed)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                sms.get("id"),
                sms.get("raw_sms", sms.get("body", "")),
                sms.get("sender", "Unknown"),
                sms.get("received_at", datetime.now().isoformat() if isinstance(datetime.now().isoformat(), str) else str(datetime.now().isoformat())),
                sms.get("confidence", 0.0)
            ))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save unclassified SMS: {e}")
            return False

    def get_unclassified_sms(self) -> list:
        """جلب جميع الرسائل غير المصنفة المراد مراجعتها"""
        try:
            rows = self._conn.execute(
                "SELECT * FROM unclassified_sms WHERE reviewed = 0 ORDER BY received_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"❌ Failed to get unclassified SMS list: {e}")
            return []

    def delete_unclassified_sms(self, sms_id: str) -> bool:
        """حذف رسالة غير مصنفة بعد معالجتها أو تجاهلها"""
        try:
            self._conn.execute("DELETE FROM unclassified_sms WHERE id = ?", (sms_id,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete unclassified SMS: {e}")
            return False

    def update_transaction_fields(self, tx_id: str, type_val: str, amount: float, counterpart: str, balance_after: float, wallet_id: str) -> bool:
        """تحديث حقول عملية موجودة لتعديلها وتصحيحها يدوياً"""
        try:
            self._conn.execute("""
                UPDATE transactions
                SET type = ?, amount = ?, counterpart = ?, balance_after = ?, wallet_id = ?
                WHERE transaction_id = ?
            """, (type_val, amount, counterpart, balance_after, wallet_id, tx_id))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update transaction fields: {e}")
            return False

    def is_license_active(self) -> bool:
        """Check if cached license is active and not expired."""
        try:
            lic_key = self.get_setting("license_key", "")
            lic_expiry_str = self.get_setting("license_expiry", "")
            lic_status = self.get_setting("license_status", "EXPIRED")
            
            if not lic_key or lic_status != "ACTIVE":
                return False
                
            from datetime import datetime
            expiry = datetime.fromisoformat(lic_expiry_str.replace("Z", "+00:00"))
            now_utc = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
            return expiry > now_utc
        except Exception as e:
            logger.error(f"Error checking is_license_active: {e}")
            return False

    def get_cached_patterns(self) -> list:
        """استرجاع الأنماط المخزنة محلياً لتمريرها للمحرك"""
        try:
            import json
            rows = self._conn.execute("SELECT pattern_id, type, regex_pattern, groups_json FROM cached_patterns").fetchall()
            patterns = []
            for row in rows:
                try:
                    groups = json.loads(row["groups_json"])
                except Exception:
                    groups = {}
                patterns.append({
                    "id": row["pattern_id"],
                    "type": row["type"],
                    "regex": row["regex_pattern"],
                    "groups": groups
                })
            return patterns
        except Exception as e:
            logger.error(f"Error retrieving cached patterns: {e}")
            return []

    def save_cached_patterns(self, patterns_list: list) -> bool:
        """حفظ الأنماط القادمة من السيرفر وتحديث الكاش المحلي"""
        try:
            import json
            self._conn.execute("DELETE FROM cached_patterns")
            for p in patterns_list:
                self._conn.execute(
                    "INSERT OR REPLACE INTO cached_patterns (pattern_id, type, regex_pattern, groups_json) VALUES (?, ?, ?, ?)",
                    (p["id"], p["type"], p["regex"], json.dumps(p["groups"]))
                )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error caching patterns: {e}")
            return False


