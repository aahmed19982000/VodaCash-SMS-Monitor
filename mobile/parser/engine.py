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
        # 1. فلترة الرسائل: قبول فقط الأرقام الرسمية والجهات المعتمدة
        if sender and not SMSClassifier.is_official_sender(sender):
            return Transaction(type=TransactionType.UNKNOWN, raw_sms=raw_sms, confidence=0.0)

        # تحديد المحفظة / الحساب
        wallet_id = SMSClassifier.detect_wallet(sender, raw_sms)

        # 2. محاولة مطابقة الأنماط الثابتة (Regex Patterns)
        for pattern_info in PATTERNS:
            match = pattern_info["regex"].search(raw_sms)
            if match:
                tx = SMSEngine._create_transaction(match, pattern_info, raw_sms)
                tx.wallet_id = wallet_id
                
                # 3. تطبيق خوارزمية درجة الثقة
                tx.confidence = SMSClassifier.calculate_confidence(raw_sms, tx, pattern_info["type"])
                
                return tx
        
        # 3. محاولة التحليل الذكي المرن (Heuristic Fallback) كخطة بديلة
        tx_heuristic = SMSEngine._parse_heuristic(raw_sms, sender, wallet_id)
        if tx_heuristic.type != TransactionType.UNKNOWN and tx_heuristic.confidence >= CONFIDENCE_THRESHOLD:
            return tx_heuristic

        # 4. إذا لم يتطابق أي نمط وفشل التحليل الذكي، نرجع عملية غير مصنفة
        return Transaction(type=TransactionType.UNKNOWN, raw_sms=raw_sms, confidence=0.0, wallet_id=wallet_id)

    @staticmethod
    def _parse_heuristic(raw_sms: str, sender: str, wallet_id: str) -> Transaction:
        """
        محلل بديل ذكي (Heuristic Fallback Parser) لاستخراج الحقول تلقائياً.
        """
        tx_type = SMSClassifier.classify_type_preliminary(raw_sms)
        if tx_type == TransactionType.UNKNOWN:
            return Transaction(type=TransactionType.UNKNOWN, raw_sms=raw_sms, confidence=0.0, wallet_id=wallet_id)

        # استخراج الأرقام مع زيادة نافذة السياق إلى 35 حرفاً
        numbers_with_context = []
        for match in re.finditer(r'(\d+(?:\.\d+)?)', raw_sms):
            num_val = float(match.group(1))
            start_idx = match.start()
            context_before = raw_sms[max(0, start_idx-35):start_idx].lower()
            context_after = raw_sms[start_idx+len(match.group(1)):start_idx+len(match.group(1))+35].lower()
            numbers_with_context.append({
                "value": num_val,
                "str": match.group(1),
                "before": context_before,
                "after": context_after,
                "start": start_idx
            })

        if not numbers_with_context:
            return Transaction(type=tx_type, raw_sms=raw_sms, confidence=0.3, wallet_id=wallet_id)

        amount = 0.0
        balance = -1.0
        trx_id = ""
        counterpart = ""

        amount_prefix_kws = ["بمبلغ", "مبلغ", "قيمة", "شحن", "خصم", "سحب", "تحويل", "received", "sent", "amount"]
        amount_postfix_kws = ["جنيه", "جنية", "جم", "egp", "le"]
        balance_kws = ["رصيدك", "رصيد", "الحالي", "الرصيد", "balance", "bal", "رصيد حسابك"]

        # حساب النقاط لكل رقم لمعرفة ما إذا كان مبلغاً أو رصيداً
        scored_numbers = []
        for num in numbers_with_context:
            if len(num["str"]) >= 10:
                continue

            # حساب نقاط المبلغ
            amt_score = 0
            for kw in amount_prefix_kws:
                if kw in num["before"]:
                    dist = len(num["before"]) - num["before"].rfind(kw)
                    if dist <= 25:
                        amt_score += 25 - dist
            for kw in amount_postfix_kws:
                if kw in num["after"]:
                    dist = num["after"].find(kw)
                    if dist <= 25:
                        amt_score += 25 - dist

            # حساب نقاط الرصيد (مؤشرات الرصيد تأتي دائماً قبل قيمة الرصيد)
            bal_score = 0
            for kw in balance_kws:
                if kw in num["before"]:
                    dist = len(num["before"]) - num["before"].rfind(kw)
                    if dist <= 35:
                        bal_score += 35 - dist

            scored_numbers.append({
                "num": num,
                "amount_score": amt_score,
                "balance_score": bal_score
            })

        if scored_numbers:
            if tx_type == TransactionType.BALANCE:
                # في حالة استعلام الرصيد، الرقم ذو نقاط الرصيد الأعلى هو الرصيد والمبلغ صفر
                best_bal = max(scored_numbers, key=lambda x: x["balance_score"])
                balance = best_bal["num"]["value"]
                amount = 0.0
            else:
                # العمليات العادية
                if len(scored_numbers) == 1:
                    # إذا كان هناك رقم واحد فقط
                    if scored_numbers[0]["balance_score"] > scored_numbers[0]["amount_score"] + 10:
                        balance = scored_numbers[0]["num"]["value"]
                        amount = 0.0
                    else:
                        amount = scored_numbers[0]["num"]["value"]
                        balance = -1.0
                else:
                    # نختار أعلى قيمة للمبلغ
                    best_amt = max(scored_numbers, key=lambda x: x["amount_score"])
                    amount = best_amt["num"]["value"]
                    
                    # الباقي هو مرشح للرصيد
                    remaining = [x for x in scored_numbers if x != best_amt]
                    if remaining:
                        best_bal = max(remaining, key=lambda x: x["balance_score"])
                        # نقبل الرصيد فقط لو كان له نقاط إيجابية
                        if best_bal["balance_score"] > 0:
                            balance = best_bal["num"]["value"]

        # 3. تخمين رقم العملية (Transaction ID)
        trx_id_candidate = None
        for num in numbers_with_context:
            if len(num["str"]) >= 10 and not num["str"].startswith("01"):
                trx_id_candidate = num["str"]
                break
        if not trx_id_candidate:
            for num in numbers_with_context:
                if len(num["str"]) >= 8 and not num["str"].startswith("01"):
                    trx_id_candidate = num["str"]
                    break
        trx_id = trx_id_candidate if trx_id_candidate else ""

        # 4. تخمين الطرف الآخر (Counterpart)
        phone_match = re.search(r'(01\d{9})', raw_sms)
        if phone_match:
            counterpart = phone_match.group(1)
        else:
            if tx_type == TransactionType.SENT:
                prefixes = ["إلى", "لـ", "لرقم", "to"]
            elif tx_type == TransactionType.RECEIVED:
                prefixes = ["من", "from"]
            else:
                prefixes = ["من", "إلى", "لـ", "لرقم", "from", "to"]

            prefix_pattern = "|".join(prefixes)
            name_match = re.search(
                rf'(?:{prefix_pattern})\s+([A-Za-z\u0621-\u064a\s\-\*]+?)(?:\s*[\.,\u060c]|\s+(?:to|from|your|account|trx|ref|date|time|egp|le|sum|رصيد|رصيدك|رقم|من|إلى|لـ|لرقم|$))',
                raw_sms,
                re.IGNORECASE
            )
            if name_match:
                name = name_match.group(1).strip()
                if len(name) > 2 and not any(w in name.lower() for w in ["مبلغ", "جنيه", "جنية", "رصيد", "حسابكم", "حسابك"]):
                    counterpart = name

        # 5. تخمين التاريخ والوقت
        sms_timestamp = datetime.now()
        date_match = re.search(r'(\d{2,4}-\d{2}-\d{2,4})', raw_sms)
        time_match = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', raw_sms)
        date_short_match = re.search(r'(?:يوم|تاريخ)\s+(\d{2}-\d{2})', raw_sms)
        
        if date_match and time_match:
            try:
                date_str = date_match.group(1)
                time_str = time_match.group(1)[:5]
                parts = date_str.split('-')
                if len(parts[0]) == 4:
                    sms_timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                elif len(parts[2]) == 4:
                    sms_timestamp = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
                else:
                    sms_timestamp = datetime.strptime(f"20{date_str} {time_str}", "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    sms_timestamp = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%y %H:%M")
                except Exception:
                    pass
        elif date_short_match and time_match:
            try:
                date_str = date_short_match.group(1)
                time_str = time_match.group(1)[:5]
                current_year = datetime.now().year
                p1, p2 = map(int, date_str.split('-'))
                if p2 > 12:
                    month, day = p1, p2
                elif p1 > 12:
                    month, day = p2, p1
                else:
                    month, day = p1, p2
                sms_timestamp = datetime(current_year, month, day, int(time_str[:2]), int(time_str[3:]))
            except Exception:
                pass

        # حساب درجة الثقة
        confidence = 0.50
        if amount > 0 or tx_type == TransactionType.BALANCE:
            confidence += 0.15
        if balance > 0:
            confidence += 0.10
        if trx_id:
            confidence += 0.05
        if counterpart:
            confidence += 0.05

        confidence = min(confidence, 0.85)

        return Transaction(
            type=tx_type,
            amount=amount,
            balance_after=balance,
            counterpart=counterpart,
            transaction_id=trx_id if trx_id else None,
            raw_sms=raw_sms,
            sms_timestamp=sms_timestamp,
            confidence=confidence,
            wallet_id=wallet_id
        )

    @staticmethod
    def _create_transaction(match: re.Match, pattern_info: dict, raw_sms: str) -> Transaction:
        groups = pattern_info["groups"]
        
        # استخراج البيانات الأساسية
        amount = float(match.group(groups["amount"])) if "amount" in groups else 0.0
        balance = float(match.group(groups["balance"])) if "balance" in groups else -1.0
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
            confidence=0.0
        )
