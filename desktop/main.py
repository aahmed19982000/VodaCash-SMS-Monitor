# desktop/main.py
# ── نقطة الدخول الرئيسية لتطبيق سطح المكتب ──────────────────────────────

import asyncio
import logging
import signal
import sys
from datetime import datetime
import threading
import subprocess
import platform

import flet as ft

from desktop.server import DesktopServer
from desktop.db.database import DesktopDatabase
from desktop.ui.app import DesktopApp
from shared.models import Transaction

# ── إعداد الـ Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VodaCash.Desktop")

class MainApplication:
    def __init__(self):
        self.db = DesktopDatabase()
        self.server = DesktopServer()
        self.ui_app = None
        
        # ربط الـ Callbacks
        self.server.on_transaction(self.handle_transaction)
        self.server.on_balance_update(self.handle_balance)
        self.server.on_unclassified(self.handle_unclassified)
        self.server.on_client_connected(self.handle_connected)
        self.server.on_client_disconnected(self.handle_disconnected)

    # ── إشعارات الديسكتوب ────────────────────────────────────────────────
    
    def send_notification(self, title: str, message: str):
        """إرسال إشعار على سطح المكتب (يدعم macOS حالياً)"""
        if platform.system() == "Darwin":
            try:
                apple_script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', apple_script])
            except Exception as e:
                logger.error(f"❌ Failed to send notification: {e}")
        else:
            # يمكن إضافة دعم لويندوز/لينكس لاحقاً هنا عبر plyer مثلاً
            pass

    # ── Callbacks للـ WebSocket ──────────────────────────────────────────

    def handle_transaction(self, tx: Transaction):
        """عند استقبال عملية من الموبايل"""
        logger.info(f"💰 Received Transaction: {tx.type.value} | {tx.amount} EGP")
        
        # 0. إرسال إشعار على الديسكتوب
        title = f"Vodafone Cash: {tx.type.value}"
        message = f"Amount: {tx.amount} EGP\nBalance: {tx.balance_after} EGP"
        self.send_notification(title, message)
        
        # 1. حفظ في قاعدة البيانات المحلية للديسكتوب
        self.db.save_transaction(tx)
        
        # 2. تحديث واجهة المستخدم لو كانت شغالة
        if self.ui_app:
            self.ui_app.refresh_views()

        # 3. إرسال تحديث للموبايل عبر WebSocket
        from shared.protocol import make_new_transaction, make_balance_update
        asyncio.create_task(self.server._broadcast(make_new_transaction(tx)))
        asyncio.create_task(self.server._broadcast(make_balance_update(tx.balance_after, tx.wallet_id)))

    def handle_balance(self, balance: float, wallet_id: str):
        logger.info(f"💳 Balance Update: {balance} EGP")
        # سيتم تحديثه في الـ Dashboard تلقائياً مع العمليات

    def handle_unclassified(self, payload: dict):
        logger.warning("📬 Received Unclassified SMS")

    def handle_connected(self, client: str):
        logger.info(f"📱 Mobile connected: {client}")
        # طلب مزامنة العمليات التي لم تصل
        asyncio.create_task(self.server.request_sync())

        # إرسال الرصيد الحالي للعميل الجديد
        kpi = self.db.get_kpi_summary()
        current_balance = kpi.get('current_balance', 0.0)
        from shared.protocol import make_balance_update, make_new_transaction
        asyncio.create_task(self.server._broadcast(make_balance_update(current_balance, "vodacash")))

        # إرسال آخر 5 عمليات للعميل الجديد
        recent_txs = self.db.get_all_transactions()[:5]
        for tx in reversed(recent_txs):
            asyncio.create_task(self.server._broadcast(make_new_transaction(tx)))

        if self.ui_app:
            self.ui_app.update_connection_status(True)

    def handle_disconnected(self, client: str):
        logger.warning(f"📱 Mobile disconnected: {client}")
        # إشعار للمستخدم بانقطاع الاتصال
        self.send_notification(
            title="VodaCash: Connection Lost",
            message=f"Mobile app disconnected ({client}). Data will be queued on mobile until reconnected."
        )
        if self.ui_app:
            self.ui_app.update_connection_status(False)

    # ── تشغيل السيرفر والواجهة ──────────────────────────────────────────

    def _start_server(self):
        """تشغيل السيرفر في Thread منفصل لكي لا يوقف الـ UI"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.server.start())

    def run(self):
        logger.info("═══════════════════════════════════════════")
        logger.info("   VodaCash SMS Monitor — Desktop Server   ")
        logger.info("═══════════════════════════════════════════")

        # 1. تشغيل الـ WebSocket Server في الخلفية
        server_thread = threading.Thread(target=self._start_server, daemon=True)
        server_thread.start()

        # 2. تشغيل واجهة المستخدم Flet
        def main_flet(page: ft.Page):
            self.ui_app = DesktopApp(page, self.db, self.server)

        ft.app(target=main_flet)

if __name__ == "__main__":
    app = MainApplication()
    app.run()
