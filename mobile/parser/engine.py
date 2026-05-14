# mobile/parser/engine.py

import re
from datetime import datetime
from shared.models import Transaction, TransactionType
from shared.config import CONFIDENCE_THRESHOLD
from mobile.parser.patterns import PATTERNS
from mobile.parser.classifier import SMSClassifier

class SMSEngine:
    @staticmethod
    def parse(raw_sms: str, sender: str = None) -> Transaction:
        """
        المنطق الرئيسي للتحليل (Main Parsing Logic).
        """
        # 1. فلترة الرسائل: قبول فقط الأرقام الرسمية
        if sender and not SMSClassifier.is_official_sender(sender):
            return Transaction(type=TransactionType.UNKNOWN, raw_sms=raw_sms, confidence=0.0)

        # 2. محاولة مطابقة الأنماط
        for pattern_info in PATTERNS:
            match = pattern_info["regex"].search(raw_sms)
            if match:
                tx = SMSEngine._create_transaction(match, pattern_info, raw_sms)
                
                # 3. تطبيق خوارزمية درجة الثقة
                tx.confidence = SMSClassifier.calculate_confidence(raw_sms, tx, pattern_info["type"])
                
                return tx
        
        # 4. إذا لم يتطابق أي نمط، نرجع عملية غير مصنفة
        return Transaction(type=TransactionType.UNKNOWN, raw_sms=raw_sms, confidence=0.0)

    @staticmethod
    def _create_transaction(match: re.Match, pattern_info: dict, raw_sms: str) -> Transaction:
        groups = pattern_info["groups"]
        
        # استخراج البيانات الأساسية
        amount = float(match.group(groups["amount"])) if "amount" in groups else 0.0
        balance = float(match.group(groups["balance"])) if "balance" in groups else 0.0
        trx_id = match.group(groups["trx_id"]) if "trx_id" in groups else ""
        counterpart = ""
        
        if "counterpart" in groups:
            counterpart = match.group(groups["counterpart"])
        elif "merchant" in groups:
            counterpart = match.group(groups["merchant"]).strip()
        
        # معالجة التاريخ والوقت
        sms_timestamp = datetime.now()
        try:
            if "date_long" in groups and "time_long" in groups:
                date_str = match.group(groups["date_long"])
                time_str = match.group(groups["time_long"])
                sms_timestamp = datetime.strptime(f"{date_str} {time_str}", "%B %d, %Y %I:%M:%S %p")
            elif "date" in groups and "time" in groups:
                date_str = match.group(groups["date"])
                time_str = match.group(groups["time"])
                parts = date_str.split('-')
                if parts[0] == '26': # YY-MM-DD
                    sms_timestamp = datetime.strptime(f"20{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
                elif parts[2] == '26': # DD-MM-YY
                    sms_timestamp = datetime.strptime(f"{date_str} {time_str[:5]}", "%d-%m-%y %H:%M")
                else:
                    sms_timestamp = datetime.strptime(f"{date_str} {time_str[:5]}", "%d-%m-%y %H:%M")
        except Exception:
            pass

        return Transaction(
            type=pattern_info["type"],
            amount=amount,
            balance_after=balance,
            counterpart=counterpart,
            transaction_id=trx_id if trx_id else None,
            raw_sms=raw_sms,
            sms_timestamp=sms_timestamp,
            confidence=0.0 # سيتم حسابه في parse()
        )
