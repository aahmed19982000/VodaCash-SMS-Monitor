# shared/config.py

# ── الاتصال بين الموبايل والديسكتوب ──────────────────────────────────────
WEBSOCKET_HOST = "0.0.0.0"   # الديسكتوب يستقبل على كل الـ interfaces
WEBSOCKET_PORT = 8765         # البورت الافتراضي

# ── فودافون كاش ──────────────────────────────────────────────────────────
VODAFONE_CASH_SENDERS = [
    "VodafoneCash",
    "VodaCash",
    "01010",
    "Vodafone",
]

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