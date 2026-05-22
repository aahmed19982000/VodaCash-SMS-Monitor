# scratch/debug_atm_regex.py
import sys, re
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AMOUNT = r"(\d+(?:\.\d+)?)"
TIME = r"(\d{2}:\d{2}(?::\d{2})?)"

# Bank ATM pattern test
pattern = re.compile(
    r"تم خصم\s+" + AMOUNT + r"EGP\s+من بطاقة.*?(?:ATM|صراف)" +
    r".*?(?:يوم|تاريخ)\s+(?P<date_slash>\d{2}/\d{2})\s+(?:الساعه?|الساعة)?\s*" + TIME +
    r".*?(?:المتاح|الرصيد|المتاح:?)\s+" + AMOUNT,
    re.IGNORECASE | re.DOTALL
)

sms = "تم خصم 4200.00EGP من بطاقة الخصم المباشر رقم 1950 عند NBE ATM031 يوم 06/08 الساعه 18:33 المتاح 10413.45 للمزيد إتصل ب 19623"
m = pattern.search(sms)
if m:
    print("Match found!")
    for i, g in enumerate(m.groups()):
        print(f"  Group {i+1}: {g}")
    print("Named groups:", m.groupdict())
else:
    print("No match found")

# Wallet ATM pattern test
AMOUNT2 = r"(\d+(?:\.\d+)?)"
TIME2 = r"(\d{2}:\d{2}(?::\d{2})?)"
DATE2 = r"(\d{2}-\d{2}-\d{2})"

pat2 = re.compile(
    r"تم سحب\s+(?:مبلغ\s+)?" + AMOUNT2 + r"\s*جني[هة]\s+من محفظة" +
    r".*(?:رصيد حسابك الحالي|رصيدك الحالي)\s+" + AMOUNT2 +
    r".*(?:تاريخ العملية|تاريخ العملية\s+‎?)\s*" + r"(?:" + TIME2 + r"\s+" + DATE2 + r"|" + DATE2 + r"\s+" + TIME2 + r")" +
    r".*(?:رقم العملية[;؛]?\s*)" + r"(\d{10,15})",
    re.IGNORECASE | re.DOTALL
)

tests = [
    "تم سحب مبلغ 200.00 جنيه من محفظة فودافون كاش؛ رصيد حسابك الحالي 0.98 جنيه. تاريخ العملية ‎23-07-25 22:26؛ رقم العملية 012918985998.",
    "تم سحب 200.00 جنية من محفظة فودافون كاش. رصيد حسابك الحالي 4082.27 جنيه. تاريخ العملية ‎30-07-25 20:05 رقم العملية; 013052181963.",
    "تم سحب 1000.00 جنية من محفظة فودافون كاش. رصيد حسابك الحالي 386.31 جنيه. تاريخ العملية 14:25 26-05-09 رقم العملية; 019839760116.",
]
for sms in tests:
    m2 = pat2.search(sms)
    if m2:
        print(f"Wallet ATM match: {m2.groups()}")
    else:
        print(f"No wallet ATM match for: {sms[:60]}")
