# mobile/sms_receiver.py
# ── الجسر بين Android BroadcastReceiver و Python Parser ──────────────────

import httpx
import threading
import logging
from datetime import datetime
from shared.models import Transaction, TransactionType, UnclassifiedSMS
from shared.config import CONFIDENCE_THRESHOLD
from mobile.parser.engine import SMSEngine
from mobile.parser.classifier import SMSClassifier
from mobile.db.database import MobileDatabase

logger = logging.getLogger("VodaCash.SmsReceiver")


class SmsReceiver:
    """
    الطبقة الوسيطة بين نظام Android و محرك التحليل.
    تستقبل الرسائل، تحللها، تخزنها محلياً، وتقرر مصيرها.
    """

    def __init__(self, broadcaster=None):
        self._broadcaster = broadcaster
        self._db = MobileDatabase()
        self._processed_count = 0
        self._rejected_count = 0

    def on_sms_received(self, sender: str, body: str, timestamp: int = None) -> Transaction:
        """
        نقطة الدخول الرئيسية — تُستدعى من Android عند وصول رسالة.
        """
        # 1. فلترة المرسل
        if not SMSClassifier.is_official_sender(sender):
            self._rejected_count += 1
            return Transaction(type=TransactionType.UNKNOWN, raw_sms=body, confidence=0.0)

        # 2. تحليل الرسالة
        tx = SMSEngine.parse(body, sender=sender)

        # 3. تعيين وقت الاستلام
        if timestamp:
            tx.sms_timestamp = datetime.fromtimestamp(timestamp / 1000.0)

        # 4. التقرير بناءً على درجة الثقة
        if tx.confidence >= CONFIDENCE_THRESHOLD:
            self._processed_count += 1

            # حفظ في قاعدة البيانات المحلية
            self._db.save_transaction(tx)

            # إرسال عبر Broadcaster للديسكتوب
            if self._broadcaster:
                self._broadcaster.broadcast_transaction(tx)
                
            # الرفع الفوري للسيرفر المركزي إن أمكن
            self.upload_transaction_to_server(tx)
        else:
            # رسالة غير مصنفة
            unclassified = UnclassifiedSMS(
                raw_sms=body, sender=sender, confidence=tx.confidence
            )
            self._db.save_unclassified(unclassified)

            if self._broadcaster:
                self._broadcaster.broadcast_unclassified(unclassified)

        return tx

    def upload_transaction_to_server(self, tx: Transaction):
        """الرفع الفوري للمعاملة إلى السيرفر المركزي بشكل منفصل"""
        direct_sync = self._db.get_setting("direct_sync", "0") == "1"
        if not direct_sync:
            return

        server_url = self._db.get_setting("server_url", "http://127.0.0.1:8000/api")
        license_key = self._db.get_setting("license_key", "")
        if not license_key:
            logger.warning("⚠️ Cannot sync directly to server: No license key configured.")
            return

        def _run():
            try:
                api_url = f"{server_url}/transactions/"
                payload = tx.to_dict()
                payload["license_key"] = license_key
                payload["profit_status"] = tx.profit_status
                
                response = httpx.post(api_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        self._db.mark_server_synced([tx.transaction_id])
                        logger.info(f"✅ Transaction {tx.transaction_id} synced directly to server successfully.")
                        return
                logger.warning(f"⚠️ Direct sync failed for {tx.transaction_id}: {response.status_code} {response.text}")
            except Exception as e:
                logger.error(f"❌ Connection error during direct transaction sync: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def sync_pending(self):
        """إرسال العمليات المعلقة التي لم تتم مزامنتها مع الديسكتوب."""
        unsynced = self._db.get_unsynced_transactions()
        if not unsynced or not self._broadcaster:
            return 0

        synced_ids = []
        for tx in unsynced:
            if self._broadcaster.broadcast_transaction(tx):
                synced_ids.append(tx.transaction_id)

        if synced_ids:
            self._db.mark_synced(synced_ids)
            self._db.log_sync(len(synced_ids))

        return len(synced_ids)

    def sync_server_pending(self):
        """مزامنة كافة المعاملات غير المرفوعة للسيرفر تلقائياً"""
        direct_sync = self._db.get_setting("direct_sync", "0") == "1"
        if not direct_sync:
            return 0
            
        unsynced = self._db.get_unsynced_server_transactions()
        if not unsynced:
            return 0
            
        server_url = self._db.get_setting("server_url", "http://127.0.0.1:8000/api")
        license_key = self._db.get_setting("license_key", "")
        if not license_key:
            return 0

        logger.info(f"🔄 Found {len(unsynced)} unsynced transactions for cloud server. Syncing...")
        success_count = 0
        for tx in unsynced:
            try:
                api_url = f"{server_url}/transactions/"
                payload = tx.to_dict()
                payload["license_key"] = license_key
                payload["profit_status"] = tx.profit_status
                
                response = httpx.post(api_url, json=payload, timeout=8.0)
                if response.status_code == 200 and response.json().get("success", False):
                    self._db.mark_server_synced([tx.transaction_id])
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ Error syncing transaction {tx.transaction_id} to server: {e}")
                break # توقف عند انقطاع الاتصال
                
        if success_count > 0:
            logger.info(f"📊 Cloud sync complete: {success_count}/{len(unsynced)} successfully uploaded.")
        return success_count

    @property
    def stats(self) -> dict:
        db_stats = self._db.get_stats()
        return {
            "processed": self._processed_count,
            "rejected": self._rejected_count,
            **db_stats,
        }
