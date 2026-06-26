# mobile/main.py
import flet as ft
import logging
import json
import threading
import time
from mobile.ui.app import MobileApp
from mobile.db.database import MobileDatabase
from mobile.broadcaster import Broadcaster
from mobile.sms_receiver import SmsReceiver
from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT

logging.basicConfig(level=logging.INFO, format='%(asctime)s │ %(name)-18s │ %(levelname)-5s │ %(message)s')
logger = logging.getLogger("VodaCash.Mobile")

def main(page: ft.Page):
    page.title = "دفتر كاش - Daftar Cash"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # تهيئة قاعدة البيانات المحلية
    db = MobileDatabase()
    
    # تهيئة الـ Broadcaster للاتصال بالديسكتوب
    broadcaster = Broadcaster(
        host=WEBSOCKET_HOST,
        port=WEBSOCKET_PORT,
    )
    
    # تهيئة مستلم الرسائل
    sms_receiver = SmsReceiver(broadcaster)
    
    # بناء الواجهة
    app = MobileApp(page, db, broadcaster)
    page.add(app)
    
    # استماع لأحداث الـ MethodChannel القادمة من الـ Java Plugin
    def on_keyboard_event(e: ft.KeyboardEvent):
        pass
        
    def on_platform_message(e):
        logger.info(f"Received platform message: {e.data}")
        try:
            data = json.loads(e.data)
            sender = data.get("sender")
            body = data.get("body")
            timestamp = data.get("timestamp")
            if sender and body:
                tx = sms_receiver.on_sms_received(sender, body, timestamp)
                logger.info(f"Processed transaction {tx.transaction_id} from platform message. Confidence: {tx.confidence}")
        except Exception as ex:
            logger.error(f"Error parsing platform message: {ex}")
            
    page.on_keyboard_event = on_keyboard_event
    page.on_platform_message = on_platform_message
    
    # محاولة الاتصال بالديسكتوب فور التشغيل
    broadcaster.start()

    # تشغيل حلقة المزامنة الخلفية التلقائية (مزامنة الديسكتوب + السيرفر)
    def background_sync_loop():
        logger.info("🔄 Started mobile background sync loop...")
        while True:
            try:
                # 1. المزامنة مع الديسكتوب إذا كان متصلاً
                if broadcaster.is_connected:
                    synced_desktop = sms_receiver.sync_pending()
                    if synced_desktop > 0:
                        logger.info(f"Sync: {synced_desktop} transactions synced to desktop.")
                
                # 2. المزامنة مع السيرفر المركزي (Cloud Server)
                synced_server = sms_receiver.sync_server_pending()
                if synced_server > 0:
                    logger.info(f"Sync: {synced_server} transactions synced to central server.")
                    
            except Exception as e:
                logger.error(f"Error in mobile background sync loop: {e}")
                
            time.sleep(30)

    threading.Thread(target=background_sync_loop, daemon=True, name="Mobile-Sync-Loop").start()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="mobile/assets")
