# shared/config.py

# ── الاتصال بين الموبايل والديسكتوب ──────────────────────────────────────
WEBSOCKET_HOST = "0.0.0.0"   # الديسكتوب يستقبل على كل الـ interfaces
WEBSOCKET_PORT = 8765         # البورت الافتراضي

# ── المحافظ والجهات المدعومة ──────────────────────────────────────────────────
WALLET_SENDERS = {
    "vodafone_cash": [
        "VodafoneCash", "VodaCash", "01010", "Vodafone", "VF Cash", "VF-Cash", "VFCash", "vf_cash", "858", "2000"
    ],
    "orange_cash": [
        "Orange Cash", "OrangeCash", "Orange", "Orange-Cash", "orange_cash", "7770"
    ],
    "etisalat_cash": [
        "EtisalatCash", "Etisalat Cash", "Etisalat", "Etisalat-Cash", "etisalat_cash"
    ],
    "we_pay": [
        "WEPay", "WE Pay", "WE_Pay", "WE", "we_cash"
    ],
    "instapay": [
        "InstaPay", "InstaPay Egypt", "IPN"
    ],
    "bank": [
        "CIB", "CIB Egypt", "NBE", "BM", "Banque Misr", "QNB", "QNB Egypt", "AlexBank", "HSBC", "AAIB"
    ]
}

# للاتساق مع الكود القديم
VODAFONE_CASH_SENDERS = WALLET_SENDERS["vodafone_cash"]

# ── الـ Parser ────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.7    # أقل من كده → unclassified

# ── الإشعارات ─────────────────────────────────────────────────────────────
NOTIFY_ON_EVERY_RECEIVED = True
NOTIFY_AMOUNT_THRESHOLD  = 1000.0   # إشعار خاص لو المبلغ أكبر من كده

# ── قاعدة البيانات ────────────────────────────────────────────────────────
MOBILE_DB_PATH  = "mobile/db/vodacash_mobile.db"
DESKTOP_DB_PATH = "desktop/db/vodacash_desktop.db"

# ── التقارير ──────────────────────────────────────────────────────────────
REPORTS_OUTPUT_DIR = "desktop/reports/output/"

# ── الـ Heartbeat ─────────────────────────────────────────────────────────
HEARTBEAT_INTERVAL = 10       # ثواني بين كل ping وpong
CONNECTION_TIMEOUT  = 30      # ثواني قبل اعتبار الاتصال منقطع