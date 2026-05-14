# mobile/scratch/verify_database.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mobile.db.database import MobileDatabase
from mobile.parser.engine import SMSEngine
from shared.models import UnclassifiedSMS

# استخدام قاعدة بيانات مؤقتة للاختبار
db = MobileDatabase.__new__(MobileDatabase)
db._initialized = False
db.__init__(db_path="mobile/scratch/test_vodacash.db")

# ── اختبار 1: حفظ عملية مصنفة ──────────────────────────────────────────
msg = """EGP 80 were successfully transferred to 01100362614 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 1.31
Transaction date: 26-05-14 21:49
Transaction ID: 019995593948"""

tx = SMSEngine.parse(msg, sender="VodafoneCash")
db.save_transaction(tx)
print(f"✅ Saved: {tx.type.value} — {tx.amount} EGP")

# ── اختبار 2: حفظ رسالة غير مصنفة ──────────────────────────────────────
sms = UnclassifiedSMS(raw_sms="رسالة عشوائية", sender="Unknown", confidence=0.2)
db.save_unclassified(sms)
print(f"✅ Saved unclassified SMS")

# ── اختبار 3: استرجاع البيانات ──────────────────────────────────────────
recent = db.get_recent_transactions(limit=5)
print(f"📋 Recent transactions: {len(recent)}")

balance = db.get_current_balance()
print(f"💰 Current balance: {balance} EGP")

stats = db.get_stats()
print(f"📊 Stats: {stats}")

summary = db.get_daily_summary()
print(f"📅 Today's summary: {summary}")

unsynced = db.get_unsynced_transactions()
print(f"🔄 Unsynced: {len(unsynced)}")

# تنظيف
db.close()
os.remove("mobile/scratch/test_vodacash.db")
print("\n✅ All database tests passed!")
