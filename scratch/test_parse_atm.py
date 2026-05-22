# scratch/test_parse_atm.py
import sys
from mobile.parser.engine import SMSEngine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sms = "تم خصم 4200.00EGP من بطاقة الخصم المباشر رقم 1950 عند NBE ATM031 يوم 06/08 الساعه 18:33 المتاح 10413.45 للمزيد إتصل ب 19623"
tx = SMSEngine.parse(sms, "IPN")
print("Type:", tx.type)
print("Amount:", tx.amount)
print("Balance:", tx.balance_after)
print("Counterpart:", tx.counterpart)
print("Timestamp:", tx.sms_timestamp)
print("Confidence:", tx.confidence)
