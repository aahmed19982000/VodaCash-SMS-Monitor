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
        self.server.on_wallet_discovery(self.handle_wallet_discovery)

    # ── إشعارات الديسكتوب ────────────────────────────────────────────────
    
    def send_notification(self, title: str, message: str, play_default_sound: bool = True):
        """إرسال إشعار على سطح المكتب مع تشغيل الصوت إذا تم تفعيلهما"""
        # 1. التحقق من تفعيل الإشعارات
        notifications_enabled = self.db.get_setting("notifications_enabled", "true") == "true"
        if not notifications_enabled:
            return

        # 2. تشغيل الصوت إذا تم تفعيله
        sound_enabled = self.db.get_setting("sound_enabled", "true") == "true"
        if sound_enabled and play_default_sound:
            if platform.system() == "Windows":
                try:
                    import winsound
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception as se:
                    logger.error(f"⚠️ Failed to play notification sound: {se}")

        # 3. إرسال الإشعار لسطح المكتب
        if platform.system() == "Darwin":
            try:
                apple_script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', apple_script])
            except Exception as e:
                logger.error(f"❌ Failed to send notification: {e}")
        elif platform.system() == "Windows":
            try:
                escaped_title = title.replace("'", "''").replace('"', '\\"')
                escaped_message = message.replace("'", "''").replace('"', '\\"')
                ps_script = (
                    f"Add-Type -AssemblyName System.Windows.Forms; "
                    f"$notification = New-Object System.Windows.Forms.NotifyIcon; "
                    f"$notification.Icon = [System.Drawing.SystemIcons]::Information; "
                    f"$notification.BalloonTipTitle = '{escaped_title}'; "
                    f"$notification.BalloonTipText = '{escaped_message}'; "
                    f"$notification.Visible = $true; "
                    f"$notification.ShowBalloonTip(5000)"
                )
                subprocess.Popen(["powershell", "-Command", ps_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.error(f"❌ Failed to send Windows notification: {e}")

    # ── Callbacks للـ WebSocket ──────────────────────────────────────────

    def handle_transaction(self, tx: Transaction, is_live: bool = False):
        """عند استقبال عملية من الموبايل"""
        if not self.db.is_license_active():
            logger.warning(f"🚫 Transaction {tx.transaction_id} ignored: Subscription has expired or is inactive.")
            return

        # Check if transaction was already processed/read before
        if self.db.transaction_exists(tx.transaction_id, tx.raw_sms):
            logger.info(f"ℹ️ Transaction {tx.transaction_id} already read before. Ignoring completely.")
            return

        logger.info(f"💰 Received Transaction: {tx.type.value} | {tx.amount} EGP | Live: {is_live}")

        
        # 0. تشغيل صوت مميز مخصص للعمليات المباشرة
        sound_enabled = self.db.get_setting("sound_enabled", "true") == "true"
        if is_live and sound_enabled and platform.system() == "Windows":
            import threading
            def play_chime():
                try:
                    import winsound
                    # RECEIVED = Customer Withdrawal (سحب للعميل). SENT = Customer Deposit (إيداع للعميل).
                    is_incoming = (tx.type == TransactionType.RECEIVED)
                    if is_incoming:
                        # Ascending chime for incoming
                        winsound.Beep(523, 100) # C5
                        winsound.Beep(659, 100) # E5
                        winsound.Beep(784, 180) # G5
                    else:
                        # Descending chime for outgoing
                        winsound.Beep(784, 100) # G5
                        winsound.Beep(659, 100) # E5
                        winsound.Beep(523, 180) # C5
                except Exception:
                    pass
            threading.Thread(target=play_chime, daemon=True).start()

        # 1. إرسال إشعار على الديسكتوب (مع تعطيل الصوت الافتراضي للعمليات المباشرة لأننا شغلنا صوتاً مميزاً لها)
        title = f"Vodafone Cash: {tx.type.value}"
        message = f"Amount: {tx.amount} EGP\nBalance: {tx.balance_after} EGP"
        self.send_notification(title, message, play_default_sound=not is_live)
        
        # 2. حفظ في قاعدة البيانات المحلية للديسكتوب
        self.db.save_transaction(tx)
        
        # 3. تحديث واجهة المستخدم لو كانت شغالة
        if self.ui_app:
            self.ui_app.page.run_thread(self.ui_app.handle_new_transaction, tx, is_live)

        # 3. إرسال تحديث للموبايل عبر WebSocket
        from shared.protocol import make_new_transaction, make_balance_update
        asyncio.create_task(self.server._broadcast(make_new_transaction(tx)))
        asyncio.create_task(self.server._broadcast(make_balance_update(tx.balance_after, tx.wallet_id)))
        
        # 4. إرسال قائمة المحافظ المحدثة للموبايل
        import json
        kpi = self.db.get_kpi_summary()
        wallet_balances = kpi.get("wallet_balances", {})
        current_balance = kpi.get('current_balance', 0.0)
        asyncio.create_task(self.server._broadcast(json.dumps({
            "type": "WALLET_BALANCES_UPDATE",
            "payload": {
                "wallet_balances": wallet_balances,
                "current_balance": current_balance
            }
        })))

    def handle_wallet_discovery(self, wallets: list):
        """عند استقبال قائمة المحافظ المكتشفة من تاريخ الموبايل (بدون معاملات)"""
        logger.info(f"🔍 Wallets discovered from mobile history: {wallets}")
        # تحديث لوحة التحكم لعرض المحافظ المكتشفة
        if self.ui_app:
            self.ui_app.refresh_views()

    def handle_balance(self, balance: float, wallet_id: str):
        logger.info(f"💳 Balance Update: {balance} EGP")
        # سيتم تحديثه في الـ Dashboard تلقائياً مع العمليات

    def handle_unclassified(self, payload: dict):
        logger.warning(f"📬 Received Unclassified SMS from {payload.get('sender', '')}")
        self.db.save_unclassified_sms(payload)
        if self.ui_app:
            self.ui_app.page.run_thread(self.ui_app.handle_new_unclassified, payload)

        # Report telemetry to Django for future analysis
        try:
            from desktop.utils.licensing import LicensingManager
            lic_mgr = LicensingManager(db=self.db)
            import threading
            threading.Thread(
                target=lic_mgr.report_unclassified_sms,
                args=(
                    payload.get("sender", "Unknown"),
                    payload.get("raw_sms", payload.get("body", "")),
                    payload.get("received_at", "")
                ),
                daemon=True
            ).start()
        except Exception as e:
            logger.error(f"⚠️ Failed to report unclassified SMS to Django: {e}")


    def handle_connected(self, client: str):
        logger.info(f"📱 Mobile connected: {client}")
        if not self.db.is_license_active():
            logger.warning("🚫 Connection sync blocked: Subscription has expired or is inactive.")
            return
        
        # طلب مزامنة العمليات التي لم تصل
        asyncio.create_task(self.server.request_sync())


        # إرسال الرصيد الحالي للعميل الجديد
        kpi = self.db.get_kpi_summary()
        current_balance = kpi.get('current_balance', 0.0)
        wallet_balances = kpi.get("wallet_balances", {})
        from shared.protocol import make_balance_update, make_new_transaction
        asyncio.create_task(self.server._broadcast(make_balance_update(current_balance, "vodacash")))
        
        # إرسال قائمة المحافظ للعميل الجديد
        import json
        asyncio.create_task(self.server._broadcast(json.dumps({
            "type": "WALLET_BALANCES_UPDATE",
            "payload": {
                "wallet_balances": wallet_balances,
                "current_balance": current_balance
            }
        })))

        # إرسال آخر 5 عمليات للعميل الجديد
        recent_txs = self.db.get_all_transactions(limit=5)
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

        ft.app(target=main_flet, assets_dir="desktop/assets")

if __name__ == "__main__":
    app = MainApplication()
    app.run()
