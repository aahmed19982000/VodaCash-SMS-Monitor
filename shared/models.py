from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TransactionType(Enum):
    RECEIVED  = "RECEIVED"   # استلام تحويل
    SENT      = "SENT"       # إرسال تحويل
    BILL      = "BILL"       # دفع فاتورة
    PURCHASE  = "PURCHASE"   # شراء من محل
    TOPUP     = "TOPUP"      # شحن رصيد
    BALANCE   = "BALANCE"    # استعلام رصيد
    UNKNOWN   = "UNKNOWN"    # غير مصنف


@dataclass
class Transaction:
    transaction_id : str      = field(default_factory=lambda: str(uuid.uuid4()))
    type           : TransactionType = TransactionType.UNKNOWN
    amount         : float    = 0.0
    balance_after  : float    = 0.0
    counterpart    : str      = ""   # رقم الطرف الآخر أو اسم التاجر
    raw_sms        : str      = ""   # نص الرسالة الأصلي
    parsed_at      : datetime = field(default_factory=datetime.now)
    sms_timestamp  : datetime = field(default_factory=datetime.now)
    confidence     : float    = 0.0  # 0.0 → 1.0
    wallet_id      : str      = "wallet_001"