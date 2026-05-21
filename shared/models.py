# shared/models.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


# ── نوع العملية ───────────────────────────────────────────────────────────
class TransactionType(Enum):
    RECEIVED = "RECEIVED"   # استلام تحويل
    SENT     = "SENT"       # إرسال تحويل
    BILL     = "BILL"       # دفع فاتورة
    PURCHASE = "PURCHASE"   # شراء من محل
    TOPUP    = "TOPUP"      # شحن رصيد
    BALANCE  = "BALANCE"    # استعلام رصيد
    UNKNOWN  = "UNKNOWN"    # غير مصنف


# ── بيانات العملية الواحدة ────────────────────────────────────────────────
@dataclass
class Transaction:
    transaction_id : str             = field(default_factory=lambda: str(uuid.uuid4()))
    type           : TransactionType = TransactionType.UNKNOWN
    amount         : float           = 0.0
    balance_after  : float           = -1.0
    counterpart    : str             = ""        # رقم الطرف أو اسم التاجر
    raw_sms        : str             = ""        # نص الرسالة الأصلي
    parsed_at      : datetime        = field(default_factory=datetime.now)
    sms_timestamp  : datetime        = field(default_factory=datetime.now)
    confidence     : float           = 0.0       # 0.0 → 1.0
    wallet_id      : str             = "unspecified"

    def is_valid(self) -> bool:
        """العملية صالحة لو confidence فوق الحد المسموح"""
        from shared.config import CONFIDENCE_THRESHOLD
        return self.confidence >= CONFIDENCE_THRESHOLD

    def to_dict(self) -> dict:
        """تحويل لـ dict جاهز للإرسال عبر WebSocket"""
        return {
            "transaction_id" : self.transaction_id,
            "type"           : self.type.value,
            "amount"         : self.amount,
            "balance_after"  : self.balance_after,
            "counterpart"    : self.counterpart,
            "raw_sms"        : self.raw_sms,
            "parsed_at"      : self.parsed_at.isoformat(),
            "sms_timestamp"  : self.sms_timestamp.isoformat(),
            "confidence"     : self.confidence,
            "wallet_id"      : self.wallet_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """إنشاء Transaction من dict قادم عبر WebSocket"""
        return cls(
            transaction_id = data.get("transaction_id", str(uuid.uuid4())),
            type           = TransactionType(data.get("type", "UNKNOWN")),
            amount         = float(data.get("amount", 0.0)),
            balance_after  = float(data.get("balance_after", -1.0)),
            counterpart    = data.get("counterpart", ""),
            raw_sms        = data.get("raw_sms", ""),
            parsed_at      = datetime.fromisoformat(data.get("parsed_at", datetime.now().isoformat())),
            sms_timestamp  = datetime.fromisoformat(data.get("sms_timestamp", datetime.now().isoformat())),
            confidence     = float(data.get("confidence", 0.0)),
            wallet_id      = data.get("wallet_id", "unspecified"),
        )


# ── حالة الاتصال ──────────────────────────────────────────────────────────
@dataclass
class ConnectionStatus:
    is_connected   : bool     = False
    last_heartbeat : datetime = field(default_factory=datetime.now)
    device_name    : str      = ""
    ip_address     : str      = ""
    connection_type: str      = "wifi"    # wifi | usb


# ── رسالة غير مصنفة ───────────────────────────────────────────────────────
@dataclass
class UnclassifiedSMS:
    id            : str      = field(default_factory=lambda: str(uuid.uuid4()))
    raw_sms       : str      = ""
    sender        : str      = ""
    received_at   : datetime = field(default_factory=datetime.now)
    confidence    : float    = 0.0
    reviewed      : bool     = False