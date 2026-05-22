# scratch/test_atm_parsing.py
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mobile.parser.engine import SMSEngine

test_cases = [
    # Bank card ATM withdrawal (instapay)
    "تم خصم 4200.00EGP من بطاقة الخصم المباشر رقم 1950 عند NBE ATM031 يوم 06/08 الساعه 18:33 المتاح 10413.45 للمزيد إتصل ب 19623",
    "تم خصم 10000.00EGP من بطاقة الخصم المباشر رقم 1950 عند NBE ATM031 يوم 05/10 الساعه 17:00 المتاح 1528.75 للمزيد إتصل ب 19623",
    # Wallet ATM withdrawal (Vodafone Cash)
    "تم سحب مبلغ 200.00 جنيه من محفظة فودافون كاش؛ رصيد حسابك الحالي 0.98 جنيه. تاريخ العملية ‎23-07-25 22:26؛ رقم العملية 012918985998.",
    "تم سحب 200.00 جنية من محفظة فودافون كاش. رصيد حسابك الحالي 4082.27 جنيه. تاريخ العملية ‎30-07-25 20:05 رقم العملية; 013052181963. اسحب لحد 5000 جنيه",
    "تم سحب 1000.00 جنية من محفظة فودافون كاش. رصيد حسابك الحالي 386.31 جنيه. تاريخ العملية 14:25 26-05-09 رقم العملية; 019839760116. دلوقتي تقدر تسحب",
    # Normal received - should NOT be ATM
    "تم استلام مبلغ 210.00 جنيه من رقم 01102103044؛ المسجل بإسم Mohamed H ALGRWANY. رصيدك الحالي 226.28 جنيه. تاريخ العملية ‎14-08-25 11:18‎ رقم العملية 013368163226.",
    # Normal sent (transfer) - should NOT be ATM
    "تم تحويل 100.0 جنيه لرقم 01222820473 مصاريف الخدمة 1.0 جنيه رصيد حسابك فى فودافون كاش الحالي 55.32.",
]

print("=" * 70)
for sms in test_cases:
    tx = SMSEngine.parse(sms)
    print(f"Type: {tx.type.value:20s} | Amount: {tx.amount:10.2f} | Bal: {tx.balance_after:10.2f}")
    print(f"  SMS: {sms[:80]}...")
    print()
print("=" * 70)
