# mobile/parser/patterns.py

import re
from shared.models import TransactionType

# ── مكونات البناء الأساسية (Building Blocks) ──────────────────────────────────
# نمط للمبالغ: يدعم الأرقام الصحيحة والكسرية (مثال: 50 أو 449.0)
AMOUNT = r"(\d+(?:\.\d+)?)"

# نمط أرقام الهاتف: يدعم 11 رقم (محلي) أو أكثر (دولي)
PHONE = r"(\d{11,14})"

# نمط رقم العملية: عادة 12 رقم أو أكثر
TRX_ID = r"(\d{10,15})"

# نمط التاريخ: يدعم YY-MM-DD أو DD-MM-YY
DATE = r"(\d{2}-\d{2}-\d{2})"

# نمط الوقت: يدعم HH:MM أو HH:MM:SS
TIME = r"(\d{2}:\d{2}(?::\d{2})?)"

# ── القائمة الكاملة للأنماط ───────────────────────────────────────────────────

PATTERNS = [
    # 1. استلام تحويل (Received Transfer) - عربي
    # تم استلام مبلغ 50 جنيه من رقم 01002528882 ...
    {
        "id": "received_ar",
        "type": TransactionType.RECEIVED,
        "regex": re.compile(
            r"تم استلام مبلغ\s+" + AMOUNT + r"\s+جنيه من رقم\s+" + PHONE +
            r".*رصيدك الحالي:\s+" + AMOUNT +
            r".*تاريخ العملية:\s+" + TIME + r"\s+" + DATE +
            r".*رقم العملية:\s+" + TRX_ID,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "counterpart": 2, "balance": 3, "time": 4, "date": 5, "trx_id": 6}
    },

    # 2. استلام تحويل (Received Transfer) - إنجليزي (بصيغة التاريخ الطويل)
    # May 14, 2026 6:42:35 PM: Received EGP170 from 00201099437596 ...
    {
        "id": "received_en_long",
        "type": TransactionType.RECEIVED,
        "regex": re.compile(
            r"(?P<date_long>\w+\s+\d{1,2},\s+\d{4})\s+(?P<time_long>\d{1,2}:\d{2}:\d{2}\s+[APM]{2}):\s+" +
            r"Received EGP\s*" + AMOUNT + r"\s+from\s+" + PHONE +
            r".*Ref:\s+" + TRX_ID +
            r".*Available Balance:\s+" + AMOUNT,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"date_long": "date_long", "time_long": "time_long", "amount": 3, "counterpart": 4, "trx_id": 5, "balance": 6}
    },

    # 3. استلام تحويل (Received Transfer) - إنجليزي (بصيغة عادية)
    {
        "id": "received_en_short",
        "type": TransactionType.RECEIVED,
        "regex": re.compile(
            r"Received EGP\s*" + AMOUNT + r"\s+from\s+" + PHONE +
            r".*Ref:\s+" + TRX_ID +
            r".*Available Balance:\s+" + AMOUNT,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "counterpart": 2, "trx_id": 3, "balance": 4}
    },

    # 4. إرسال تحويل (Sent Transfer) - إنجليزي
    # EGP 80 were successfully transferred to 01100362614 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 1.31
    # Transaction date: 26-05-14 21:49
    # Transaction ID: 019995593948
    {
        "id": "sent_en",
        "type": TransactionType.SENT,
        "regex": re.compile(
            r"EGP\s+" + AMOUNT + r"\s+were successfully transferred to\s+" + PHONE +
            r".*balance is EGP\s+" + AMOUNT +
            r".*Transaction date:\s+" + DATE + r"\s+" + TIME +
            r".*Transaction ID:\s+" + TRX_ID,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "counterpart": 2, "balance": 3, "date": 4, "time": 5, "trx_id": 6}
    },

    # 5. إرسال تحويل (Sent Transfer) - عربي
    # تم تحويل 5 جنيه لرقم 01222820473 مصاريف الخدمة 1 جنيه رصيد حسابك فى فودافون كاش الحالي 71.31.
    {
        "id": "sent_ar",
        "type": TransactionType.SENT,
        "regex": re.compile(
            r"تم تحويل\s+(?:مبلغ\s+)?" + AMOUNT + r"\s+جنيه\s+(?:لرقم|إلى رقم|لـ|ل)\s*" + PHONE +
            r".*(?:رصيد حسابك فى فودافون كاش الحالي|رصيد حسابك في فودافون كاش الحالي|رصيدك الحالي|رصيد محفظتك الحالي)(?:\s+هو)?\s+" + AMOUNT +
            r".*رقم العملية(?:\s*:|:)?\s*" + TRX_ID,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "counterpart": 2, "balance": 3, "trx_id": 4}
    },




    # 4. دفع فاتورة (Bill Payment) - عربي
    # تم دفع مبلغ 449.0جنية لNzmly. رصيد محفظتك الحالي 103.31 جنيه.
    {
        "id": "bill_ar",
        "type": TransactionType.BILL,
        "regex": re.compile(
            r"تم دفع مبلغ\s+" + AMOUNT + r"\s*جنية ل(?P<merchant>.*?)\." +
            r".*رصيد محفظتك الحالي\s+" + AMOUNT +
            r".*رقم العملية\s+" + TRX_ID +
            r".*تاريخ العملية\s+" + DATE + r"\s+" + TIME,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "merchant": "merchant", "balance": 3, "trx_id": 4, "date": 5, "time": 6}
    },

    # 5. شحن رصيد (Recharge / Top-up) - عربي
    # (نمط مستنتج للخدمة) تم شحن رصيد بمبلغ 10 جنيه لرقم 010...
    {
        "id": "topup_ar",
        "type": TransactionType.TOPUP,
        "regex": re.compile(
            r"تم شحن رصيد بمبلغ\s+" + AMOUNT + r"\s*جنيه لرقم\s+" + PHONE +
            r".*رصيد محفظتك الحالي\s+" + AMOUNT,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 1, "counterpart": 2, "balance": 3}
    },

    # 6. شحن رصيد الموبايل الشخصي (Own Mobile Top-up) - عربي
    # تم شحن رصيد موبايلك ب 175 بنجاح وخصم 250 من محفظتك شاملة الضريبة; رصيد حسابك في فودافون كاش الحالي 77.31.
    {
        "id": "topup_own_ar",
        "type": TransactionType.TOPUP,
        "regex": re.compile(
            r"تم شحن رصيد موبايلك ب\s+" + AMOUNT + r"\s+بنجاح وخصم\s+" + AMOUNT + r"\s+من محفظتك" +
            r".*(?:رصيد حسابك في فودافون كاش الحالي|رصيد حسابك فى فودافون كاش الحالي|رصيد محفظتك الحالي|رصيدك الحالي)(?:\s+هو)?\s+" + AMOUNT,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"amount": 2, "balance": 3}
    },


    # 6. شراء من محل / أونلاين (Purchase / OTP) - عربي
    # الرقم السري المتغير الخاص بعمليه الشراء الالكترونية ... هو 321084 بمبلغ 449.0
    {
        "id": "purchase_ar",
        "type": TransactionType.PURCHASE,
        "regex": re.compile(
            r"الرقم السري المتغير الخاص بعمليه الشراء الالكترونية.*هو\s+(?P<otp>\d+)\s+بمبلغ\s+" + AMOUNT,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"otp": "otp", "amount": 2}
    },

    # 7. استعلام عن الرصيد (Balance Inquiry) - إنجليزي
    # Your current Vodafone Cash balance is 82.31 LE ...
    {
        "id": "balance_en",
        "type": TransactionType.BALANCE,
        "regex": re.compile(
            r"Your current Vodafone Cash balance is\s+" + AMOUNT + r"\s+LE" +
            r".*Trx date:\s+" + DATE + r"\s+" + TIME +
            r".*Trx ID\s+" + TRX_ID,
            re.IGNORECASE | re.DOTALL
        ),
        "groups": {"balance": 1, "date": 2, "time": 3, "trx_id": 4}
    }
]
