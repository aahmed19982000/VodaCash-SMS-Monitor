# mobile/main.py
import flet as ft
import logging
from mobile.ui.app import MobileApp
from mobile.db.database import MobileDatabase
from mobile.broadcaster import Broadcaster
from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT

logging.basicConfig(level=logging.INFO, format='%(asctime)s │ %(name)-18s │ %(levelname)-5s │ %(message)s')
logger = logging.getLogger("VodaCash.Mobile")

def main(page: ft.Page):
    page.title = "VodaCash Monitor"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # تهيئة قاعدة البيانات المحلية
    db = MobileDatabase()
    
    # تهيئة الـ Broadcaster للاتصال بالديسكتوب
    broadcaster = Broadcaster(
        host=WEBSOCKET_HOST,
        port=WEBSOCKET_PORT,
    )
    
    # بناء الواجهة
    app = MobileApp(page, db, broadcaster)
    page.add(app)
    
    # استماع لأحداث الـ MethodChannel القادمة من الـ Java Plugin
    # سنقوم باستقبال أحداث الـ SMS من الأندرويد عبر Flet channel
    def on_keyboard_event(e: ft.KeyboardEvent):
        pass
        
    def on_platform_message(e):
        logger.info(f"Received platform message: {e.data}")
        # تحليل الرسالة ومعالجتها
        
    page.on_keyboard_event = on_keyboard_event
    
    # محاولة الاتصال فور التشغيل
    broadcaster.start()

if __name__ == "__main__":
    ft.app(target=main)
