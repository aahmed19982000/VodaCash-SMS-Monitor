import re
from shared.models import TransactionType

class SMSClassifier:
    @staticmethod
    def is_official_sender(sender: str) -> bool:
        """
        التحقق مما إذا كان المرسل من المحافظ المدعومة أو مرسل رسمي (غير شخصي).
        """
        clean_sender = sender.strip().lower()
        
        # 1. تحقق من القوائم الثابتة
        from shared.config import WALLET_SENDERS
        for wallet, senders in WALLET_SENDERS.items():
            for official in senders:
                if clean_sender == official.lower():
                    return True
        
        # 2. تحقق لو كان اسم مرسل رسمي (alphanumeric) وليس رقم هاتف شخصي عادي
        # أرقام الهواتف الشخصية في مصر تكون أرقاماً بحتة بطول 11 رقم أو تبدأ بـ +20
        is_personal_phone = re.match(r'^(?:\+?20|0)?1[0125]\d{8}$', clean_sender)
        if not is_personal_phone:
            # إذا كان الاسم يحتوي على حروف أبجدية أو كود قصير (أقل من 6 أرقام)، فهو غالباً جهة/شركة
            if re.search(r'[a-z]', clean_sender) or (clean_sender.isdigit() and len(clean_sender) <= 5):
                return True
                
        return False

    @staticmethod
    def detect_wallet(sender: str, text: str) -> str:
        """
        تحديد نوع المحفظة أو الجهة بناءً على اسم المرسل ومحتوى الرسالة.
        """
        if sender:
            clean_sender = sender.strip().lower()
            from shared.config import WALLET_SENDERS
            for wallet, senders in WALLET_SENDERS.items():
                for official in senders:
                    if clean_sender == official.lower():
                        return wallet
        
        # فحص الكلمات المفتاحية في النص كخطة بديلة
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["فودافون كاش", "vodafone cash", "vodacash", "voda cash", "858", "فودافون", "vodafone"]):
            return "vodafone_cash"
        elif any(kw in text_lower for kw in ["اورنج كاش", "اورنچ كاش", "orange cash", "أورنج كاش", "أورنچ كاش", "orange_cash", "7770"]):
            return "orange_cash"
        elif any(kw in text_lower for kw in ["اتصالات كاش", "etisalat cash", "etisalat_cash"]):
            return "etisalat_cash"
        elif any(kw in text_lower for kw in ["وي باي", "we pay", "wepay", "we_pay"]):
            return "we_pay"
        elif any(kw in text_lower for kw in ["انستاباي", "instapay", "ipn", "19623", "تحويل لحظي"]):
            return "instapay"
        elif any(kw in text_lower for kw in ["cib", "nbe", "البنك الأهلي", "بنك مصر", "qnb", "حسابكم", "حسابك"]):
            return "bank"
            
        return "unspecified"

    @staticmethod
    def classify_type_preliminary(text: str) -> TransactionType:
        """
        تصنيف أولي للعملية بناءً على الكلمات المفتاحية لزيادة الثقة.
        """
        text_lower = text.lower()
        
        # 0. ATM Withdrawal - يجب أن يكون قبل SENT لمنع التصنيف الخاطئ
        # رسائل سحب ATM من محفظة فودافون كاش
        if "تم سحب" in text_lower and "من محفظة" in text_lower:
            return TransactionType.ATM_WITHDRAWAL
        # رسائل سحب ATM ببطاقة من بنك/انستاباي
        if "من بطاقة" in text_lower and ("atm" in text_lower or "صراف" in text_lower):
            return TransactionType.ATM_WITHDRAWAL

        # 1. استلام (Received)
        if any(kw in text_lower for kw in [
            "تم استلام مبلغ", "received egp", "received from", "تم استلام عملية تحويل", 
            "أودع", "إيداع", "تم إضافة", "تم تحويل مبلغ لك", "تم تحويل مبلغ لـك", 
            "تمت إضافته لرصيدك", "received", "تم استلام", "أودع في حسابك", "تم إيداع",
            "تم استقبال تحويل", "إضافة تحويل", "تحويل لحظي إلى حسابكم"
        ]):
            return TransactionType.RECEIVED
            
        # 2. إرسال (Sent)
        if any(kw in text_lower for kw in [
            "were successfully transferred", "تم تحويل", "عملية تحويل أموال ناجحة", 
            "تم خصم", "تم سحب", "خصم مبلغ", "تحويل مبلغ", "transferred", "sent to",
            "successfully sent", "تم تنفيذ تحويل", "تحويل لحظي من حسابكم", "تحويل من حسابكم", 
            "خصم من حسابكم", "تحويل لحظي"
        ]):
            return TransactionType.SENT
            
        # 3. فاتورة (Bill)
        if any(kw in text_lower for kw in ["تم دفع مبلغ", "bill paid", "payment for", "paid egp"]):
            return TransactionType.BILL
            
        # 4. شحن (Top-up)
        if any(kw in text_lower for kw in ["تم شحن رصيد", "recharged successfully", "شحن رصيد"]):
            return TransactionType.TOPUP
            
        # 5. استعلام رصيد (Balance)
        if any(kw in text_lower for kw in [
            "vodafone cash balance", "رصيد محفظتك الحالي", "رصيدك الحالي", 
            "رصيد حسابك", "رصيد محفظتك", "الرصيد الحالي", "balance is", "current balance", "balance:"
        ]):
            if "تم دفع" not in text_lower and "تم استلام" not in text_lower and "تم تحويل" not in text_lower and "received" not in text_lower:
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
