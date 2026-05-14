# mobile/scratch/verify_parser.py

import sys
import os

# إضافة المجلد الرئيسي للمسار لتمكين الاستيراد
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mobile.parser.engine import SMSEngine

messages = [
    """EGP 80 were successfully transferred to 01100362614 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 1.31
Transaction date: 26-05-14 21:49
Transaction ID: 019995593948
With every transaction you get more chances to win a Gold Coin for Mother's Day. Transfer, recharge & pay your bills through http://vf.eg/vfcash and increase your chances!""",

    """Your current Vodafone Cash balance is 82.31 LE  Trx date: 14-05-26 21:48 Trx ID 019995555928. View your transaction history on Ana Vodafone App to track your spending: http://vf.eg/vfcash""",

    """EGP 240 were successfully transferred to 01068586061 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 82.31
Transaction date: 26-05-14 18:47
Transaction ID: 019989269370
With every transaction you get more chances to win a Gold Coin for Mother's Day. Transfer, recharge & pay your bills through http://vf.eg/vfcash and increase your chances!""",

    """تم استلام مبلغ 50 جنيه من رقم 01002528882 المسجل بإسم Mohamed H Ibrahim على رقم محفظتك  01099437596.
رصيدك الحالي: 323.31 جنيه
تاريخ العملية: 18:42 26-05-14
رقم العملية: 019989114271
تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash""",

    """May 14, 2026 6:42:35 PM: Received EGP170 from 00201099437596 to Mobile Account Number 5786. Ref: 019989098425 Available Balance: 273.31""",

    """Your current Vodafone Cash balance is 103.31 LE  Trx date: 14-05-26 18:41 Trx ID 019989073560. View your transaction history on Ana Vodafone App to track your spending: http://vf.eg/vfcash""",

    """تم دفع مبلغ 449.0جنية لNzmly.  رصيد محفظتك الحالي 103.31 جنيه. رقم العملية 019951946027 تاريخ العملية 13-05-26 13:09. دلوقتي ولأول مرة تقدر تشحن أي كارت كهرباء بفودافون كاش من مكانك ,دوس على http://vf.eg/vfcash  واختار خدمة شحن كارت الكهرباء.""",

    """الرقم السري المتغير الخاص بعمليه الشراء الالكترونية من محفظة فودافون كاش هو 321084 بمبلغ 449.0. وستنتهي صلاحيته خلال 5 دقائق. برجاء عدم مشاركه هذا الرقم مع أي شخص حفاظًا على بياناتك.""",

    """تم استلام مبلغ 200.00 جنيه من رقم 01055411994 المسجل بإسم احمد جمال عبدالحكيم عبدالغفار على رقم محفظتك  01099437596.
رصيدك الحالي: 552.31 جنيه
تاريخ العملية: 12:52 26-05-13
رقم العملية: 019951584359
تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash""",

    """Your current Vodafone Cash balance is 352.31 LE  Trx date: 13-05-26 12:49 Trx ID 019951529048. View your transaction history on Ana Vodafone App to track your spending: http://vf.eg/vfcash"""
]

print(f"{'Type':<10} | {'Amount':<8} | {'Balance':<8} | {'Counterpart':<15} | {'Date'}")
print("-" * 70)

for msg in messages:
    tx = SMSEngine.parse(msg)
    date_str = tx.sms_timestamp.strftime("%Y-%m-%d %H:%M")
    print(f"{tx.type.value:<10} | {tx.amount:<8.2f} | {tx.balance_after:<8.2f} | {tx.counterpart:<15} | {date_str}")
