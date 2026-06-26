# mobile/scratch/verify_direct_sync.py
import sys
import os
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s │ %(name)-18s │ %(levelname)-5s │ %(message)s')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mobile.db.database import MobileDatabase
from mobile.sms_receiver import SmsReceiver
from shared.models import Transaction, TransactionType

def verify_sync():
    print("🧪 Starting Direct Cloud Sync Verification...")
    
    # 1. تهيئة قاعدة البيانات المحلية المؤقتة
    db_path = "mobile/scratch/test_sync_db.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db = MobileDatabase(db_path=db_path)
    
    # 2. ضبط إعدادات السيرفر ومفتاح الترخيص
    server_url = "http://127.0.0.1:8000/api"
    license_key = "test_lic_key_12345" # المفتاح المفعل في verify_central_sync.py
    
    db.set_setting("server_url", server_url)
    db.set_setting("license_key", license_key)
    db.set_setting("direct_sync", "1")
    
    print(f"⚙️ Configured local settings: URL={server_url}, Key={license_key}")
    
    # 3. تهيئة مستلم الرسائل
    sms_receiver = SmsReceiver(broadcaster=None)
    # استبدال قاعدة بيانات المستلم بقاعدة بيانات الاختبار الخاصة بنا
    sms_receiver._db = db
    
    # 4. محاكاة استقبال رسالة فودافون كاش
    sms_body = """EGP 150 were successfully transferred to 01012345678 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 500.00
Transaction date: 26-06-26 11:10
Transaction ID: 999111333222"""
    
    print("\n📩 Simulating SMS message arrival...")
    tx = sms_receiver.on_sms_received("VodafoneCash", sms_body)
    
    print(f"Parsed Transaction ID: {tx.transaction_id}")
    print(f"Amount: {tx.amount} EGP, Wallet: {tx.wallet_id}, Confidence: {tx.confidence}")
    
    # ننتظر قليلاً لكي ينتهي خيط الرفع الخلفي الفوري (Immediate Sync Thread)
    print("⏳ Waiting for direct sync thread to complete...")
    time.sleep(3)
    
    # 5. التحقق من حالة المزامنة في قاعدة البيانات المحلية
    stats = db.get_stats()
    print(f"📊 Stats after sync: {stats}")
    
    unsynced_server = db.get_unsynced_server_transactions()
    if not unsynced_server:
        print("🎉 Success! Transaction was successfully synced directly to the server (0 unsynced remaining).")
    else:
        print("⚠️ Transaction is still unsynced in local database.")
        
    # 6. اختبار المزامنة الخلفية للمعلقات (Pending Sync)
    print("\n📦 Simulating offline transaction storage and background sync...")
    # إيقاف المزامنة المباشرة مؤقتاً لحفظ معاملة محلية غير مزامنة
    db.set_setting("direct_sync", "0")
    
    sms_body_offline = """EGP 400 were successfully transferred to 01088888888 the transfer fee is EGP 1, your current Vodafone Cash balance is EGP 900.00
Transaction date: 26-06-26 11:12
Transaction ID: 999111333444"""
    tx_offline = sms_receiver.on_sms_received("VodafoneCash", sms_body_offline)
    print(f"Saved offline Transaction ID: {tx_offline.transaction_id}")
    
    # التأكد من أنها غير مزامنة
    stats_offline = db.get_stats()
    print(f"📊 Stats (offline): {stats_offline}")
    assert stats_offline["unsynced_server_transactions"] == 1
    
    # تفعيل المزامنة المباشرة وتشغيل مزامنة المعلقات يدوياً
    db.set_setting("direct_sync", "1")
    print("🔄 Running sync_server_pending()...")
    synced_count = sms_receiver.sync_server_pending()
    print(f"✅ Synced {synced_count} pending transactions to server.")
    
    # التحقق النهائي
    stats_final = db.get_stats()
    print(f"📊 Final Stats: {stats_final}")
    assert stats_final["unsynced_server_transactions"] == 0
    
    # تنظيف قاعدة البيانات المؤقتة
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n🚀 All Direct Sync Verification tests passed successfully!")

if __name__ == "__main__":
    verify_sync()
