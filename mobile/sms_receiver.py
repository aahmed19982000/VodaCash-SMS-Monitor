# mobile/sms_receiver.py
# ── الجسر بين Android BroadcastReceiver و Python Parser ──────────────────

from datetime import datetime
from shared.models import Transaction, TransactionType, UnclassifiedSMS
from shared.config import CONFIDENCE_THRESHOLD
from mobile.parser.engine import SMSEngine
from mobile.parser.classifier import SMSClassifier
from mobile.db.database import MobileDatabase


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

            # إرسال عبر Broadcaster
            if self._broadcaster:
                self._broadcaster.broadcast_transaction(tx)
        else:
            # رسالة غير مصنفة
            unclassified = UnclassifiedSMS(
                raw_sms=body, sender=sender, confidence=tx.confidence
            )
            self._db.save_unclassified(unclassified)

            if self._broadcaster:
                self._broadcaster.broadcast_unclassified(unclassified)

        return tx

    def sync_pending(self):
        """إرسال العمليات المعلقة التي لم تتم مزامنتها."""
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

    @property
    def stats(self) -> dict:
        db_stats = self._db.get_stats()
        return {
            "processed": self._processed_count,
            "rejected": self._rejected_count,
            **db_stats,
        }
