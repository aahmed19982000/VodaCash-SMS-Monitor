# mobile/parser/classifier.py

import re
from shared.config import VODAFONE_CASH_SENDERS
from shared.models import TransactionType

class SMSClassifier:
    @staticmethod
    def is_official_sender(sender: str) -> bool:
        """
        التحقق مما إذا كان المرسل من قائمة فودافون كاش الرسمية.
        """
        # تنظيف اسم المرسل (إزالة المسافات، تحويل لحروف صغيرة)
        clean_sender = sender.strip()
        for official in VODAFONE_CASH_SENDERS:
            if clean_sender.lower() == official.lower():
                return True
        return False

    @staticmethod
    def classify_type_preliminary(text: str) -> TransactionType:
        """
        تصنيف أولي للعملية بناءً على الكلمات المفتاحية لزيادة الثقة.
        """
        text_lower = text.lower()
        
        # 1. استلام (Received)
        if any(kw in text_lower for kw in ["تم استلام مبلغ", "received egp", "received from"]):
            return TransactionType.RECEIVED
            
        # 2. إرسال (Sent)
        if any(kw in text_lower for kw in ["were successfully transferred", "تم تحويل"]):
            return TransactionType.SENT

            
        # 3. فاتورة (Bill)
        if any(kw in text_lower for kw in ["تم دفع مبلغ", "bill paid", "payment for"]):
            return TransactionType.BILL
            
        # 4. شحن (Top-up)
        if any(kw in text_lower for kw in ["تم شحن رصيد", "recharged successfully"]):
            return TransactionType.TOPUP
            
        # 5. استعلام رصيد (Balance)
        if any(kw in text_lower for kw in ["vodafone cash balance", "رصيد محفظتك الحالي"]):
            if "تم دفع" not in text_lower and "تم استلام" not in text_lower:
                return TransactionType.BALANCE
                
        # 6. شراء (Purchase)
        if any(kw in text_lower for kw in ["الشراء الالكترونية", "v-card", "online purchase"]):
            return TransactionType.PURCHASE
            
        return TransactionType.UNKNOWN

    @staticmethod
    def calculate_confidence(raw_sms: str, parsed_tx: "Transaction", match_type: TransactionType) -> float:
        """
        خوارزمية حساب درجة الثقة (Confidence Score Algorithm).
        """
        score = 0.0
        
        # 1. إذا تطابق النمط (Regex Match)
        if parsed_tx.type != TransactionType.UNKNOWN:
            score += 0.6
            
        # 2. إذا تطابق التصنيف الأولي مع التصنيف النهائي
        preliminary_type = SMSClassifier.classify_type_preliminary(raw_sms)
        if preliminary_type == parsed_tx.type and parsed_tx.type != TransactionType.UNKNOWN:
            score += 0.2
            
        # 3. التحقق من وجود الحقول الأساسية
        if parsed_tx.amount > 0:
            score += 0.1
        if parsed_tx.transaction_id:
            score += 0.1
            
        return min(score, 1.0)
