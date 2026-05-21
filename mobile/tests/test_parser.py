# mobile/tests/test_parser.py

import unittest
import sys
import os

# إضافة المسار الرئيسي لتمكين الاستيراد
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mobile.parser.engine import SMSEngine
from shared.models import TransactionType

class TestVodaCashParser(unittest.TestCase):
    
    def test_sent_transfer_english(self):
        msg = """EGP 80 were successfully transferred to 01100362614 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 1.31
Transaction date: 26-05-14 21:49
Transaction ID: 019995593948"""
        tx = SMSEngine.parse(msg, sender="VodafoneCash")
        self.assertEqual(tx.type, TransactionType.SENT)
        self.assertEqual(tx.amount, 80.0)
        self.assertEqual(tx.counterpart, "01100362614")
        self.assertEqual(tx.balance_after, 1.31)
        self.assertEqual(tx.transaction_id, "019995593948")
        self.assertGreaterEqual(tx.confidence, 0.9)

        self.assertGreaterEqual(tx.confidence, 0.9)

    def test_sent_transfer_arabic_variation(self):
        msg = """كسبت 10 جنيه كاش باك تستخدمها دقائق لفودافون اوميجابيتس ب 20 قرش الوحدة! ادخل علي تطبيق انا فودافون http://vf.eg/vfcash او اطلب
 *365*90#
 قبل آخر اليوم للاستمتاع بالهدية.
تم تحويل 5 جنيه لرقم 01222820473 مصاريف الخدمة 1 جنيه رصيد حسابك فى فودافون كاش الحالي 71.31.
تاريخ العملية: 11:32 26-05-21
رقم العملية: 020173477469"""
        tx = SMSEngine.parse(msg, sender="VodafoneCash")
        self.assertEqual(tx.type, TransactionType.SENT)
        self.assertEqual(tx.amount, 5.0)
        self.assertEqual(tx.counterpart, "01222820473")
        self.assertEqual(tx.balance_after, 71.31)
        self.assertEqual(tx.transaction_id, "020173477469")
        self.assertGreaterEqual(tx.confidence, 0.9)

    def test_topup_own_arabic(self):
        msg = """تم شحن رصيد موبايلك ب 175 بنجاح وخصم 250 من محفظتك شاملة الضريبة; رصيد حسابك في فودافون كاش الحالي 77.31."""
        tx = SMSEngine.parse(msg, sender="VodafoneCash")
        self.assertEqual(tx.type, TransactionType.TOPUP)
        self.assertEqual(tx.amount, 250.0)
        self.assertEqual(tx.balance_after, 77.31)
        self.assertGreaterEqual(tx.confidence, 0.9)



    def test_received_transfer_arabic(self):
        msg = """تم استلام مبلغ 50 جنيه من رقم 01002528882 المسجل بإسم Mohamed H Ibrahim على رقم محفظتك  01099437596.
رصيدك الحالي: 323.31 جنيه
تاريخ العملية: 18:42 26-05-14
رقم العملية: 019989114271"""
        tx = SMSEngine.parse(msg, sender="Vodafone")
        self.assertEqual(tx.type, TransactionType.RECEIVED)
        self.assertEqual(tx.amount, 50.0)
        self.assertEqual(tx.counterpart, "01002528882")
        self.assertEqual(tx.balance_after, 323.31)
        self.assertGreaterEqual(tx.confidence, 0.9)

    def test_bill_payment_arabic(self):
        msg = """تم دفع مبلغ 449.0جنية لNzmly.  رصيد محفظتك الحالي 103.31 جنيه. رقم العملية 019951946027 تاريخ العملية 13-05-26 13:09."""
        tx = SMSEngine.parse(msg, sender="VodaCash")
        self.assertEqual(tx.type, TransactionType.BILL)
        self.assertEqual(tx.amount, 449.0)
        self.assertEqual(tx.counterpart, "Nzmly")
        self.assertEqual(tx.balance_after, 103.31)
        self.assertGreaterEqual(tx.confidence, 0.9)

    def test_balance_inquiry_english(self):
        msg = """Your current Vodafone Cash balance is 82.31 LE  Trx date: 14-05-26 21:48 Trx ID 019995555928."""
        tx = SMSEngine.parse(msg, sender="VodafoneCash")
        self.assertEqual(tx.type, TransactionType.BALANCE)
        self.assertEqual(tx.balance_after, 82.31)
        self.assertGreaterEqual(tx.confidence, 0.9)

    def test_sender_filtering(self):
        msg = "EGP 80 were successfully transferred..."
        # مرسل غير رسمي
        tx = SMSEngine.parse(msg, sender="Stranger")
        self.assertEqual(tx.type, TransactionType.UNKNOWN)
        self.assertEqual(tx.confidence, 0.0)

    def test_purchase_otp_arabic(self):
        msg = "الرقم السري المتغير الخاص بعمليه الشراء الالكترونية من محفظة فودافون كاش هو 321084 بمبلغ 449.0."
        tx = SMSEngine.parse(msg, sender="Vodafone")
        self.assertEqual(tx.type, TransactionType.PURCHASE)
        self.assertEqual(tx.amount, 449.0)
        self.assertGreaterEqual(tx.confidence, 0.8)

    def test_orange_cash_received(self):
        msg = """تم استلام عملية تحويل أموال بمبلغ 5.00 جنيه من Ahmed A Elsaid، رصيدك الحالي 79.28 جنية. رقم المعاملة 2951618892"""
        tx = SMSEngine.parse(msg, sender="OrangeCash")
        self.assertEqual(tx.wallet_id, "orange_cash")
        self.assertEqual(tx.type, TransactionType.RECEIVED)
        self.assertEqual(tx.amount, 5.0)
        self.assertEqual(tx.balance_after, 79.28)
        self.assertEqual(tx.transaction_id, "2951618892")
        self.assertEqual(tx.counterpart, "Ahmed A Elsaid")
        self.assertGreaterEqual(tx.confidence, 0.7)

    def test_orange_cash_balance_inquiry(self):
        msg = """رصيدك الحالي فى اورنچ كاش 79.28 جنيه. شكرا لاستخدامك اورنچ كاش"""
        tx = SMSEngine.parse(msg, sender="7770")
        self.assertEqual(tx.wallet_id, "orange_cash")
        self.assertEqual(tx.type, TransactionType.BALANCE)
        self.assertEqual(tx.balance_after, 79.28)
        self.assertGreaterEqual(tx.confidence, 0.7)

    def test_instapay_received(self):
        msg = """InstaPay: EGP 150.00 received from Mohamed Ali to your CIB account. Trx Ref: 602345678901"""
        tx = SMSEngine.parse(msg, sender="InstaPay")
        self.assertEqual(tx.wallet_id, "instapay")
        self.assertEqual(tx.type, TransactionType.RECEIVED)
        self.assertEqual(tx.amount, 150.0)
        self.assertEqual(tx.transaction_id, "602345678901")
        self.assertEqual(tx.counterpart, "Mohamed Ali")
        self.assertGreaterEqual(tx.confidence, 0.7)

    def test_we_pay_sent(self):
        msg = """تم تحويل مبلغ 100.0 جنيه لرقم 01551234567 من محفظة وي باي بنجاح. مصاريف الخدمة 2.0 جنيه. رصيدك الحالي هو 350.50 جنيه."""
        tx = SMSEngine.parse(msg, sender="WEPay")
        self.assertEqual(tx.wallet_id, "we_pay")
        self.assertEqual(tx.type, TransactionType.SENT)
        self.assertEqual(tx.amount, 100.0)
        self.assertEqual(tx.balance_after, 350.50)
        self.assertEqual(tx.counterpart, "01551234567")
        self.assertGreaterEqual(tx.confidence, 0.7)

    def test_banque_misr_instapay_sent(self):
        msg = """تم تنفيذ تحويل لحظي من حسابكم رقم 0140 بمبلغ 10.00 جم إلى احمد ا** ا** ا**** رقم مرجعي 235424765447 يوم 05-21 الساعة 14:27 للمزيد اتصل بـ 19623"""
        tx = SMSEngine.parse(msg, sender="BM")
        self.assertEqual(tx.wallet_id, "bank")
        self.assertEqual(tx.type, TransactionType.SENT)
        self.assertEqual(tx.amount, 10.00)
        self.assertEqual(tx.counterpart, "احمد ا** ا** ا****")
        self.assertEqual(tx.transaction_id, "235424765447")
        self.assertEqual(tx.sms_timestamp.month, 5)
        self.assertEqual(tx.sms_timestamp.day, 21)
        self.assertEqual(tx.sms_timestamp.hour, 14)
        self.assertEqual(tx.sms_timestamp.minute, 27)
        self.assertGreaterEqual(tx.confidence, 0.7)

if __name__ == '__main__':
    unittest.main()
