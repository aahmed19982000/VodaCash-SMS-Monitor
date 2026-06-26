# mobile/ui/app.py
import flet as ft
import httpx
import logging
from mobile.db.database import MobileDatabase
from mobile.broadcaster import Broadcaster
from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT

logger = logging.getLogger("VodaCash.MobileUI")

class MobileApp(ft.Container):
    def __init__(self, page: ft.Page, db: MobileDatabase, broadcaster: Broadcaster):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.broadcaster = broadcaster
        self.expand = True
        self.padding = 20
        self.bgcolor = "#080C14"

        # Styles matching desktop app theme
        self.input_style = {
            "border_radius": 10,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": "#1E8F8B",
            "filled": True,
            "text_size": 14,
            "label_style": ft.TextStyle(color=ft.Colors.WHITE54)
        }

        # تحميل الإعدادات المخزنة
        self.stored_server_url = self.db.get_setting("server_url", "http://127.0.0.1:8000/api")
        self.stored_license_key = self.db.get_setting("license_key", "")
        self.stored_direct_sync = self.db.get_setting("direct_sync", "0") == "1"

        # UI Elements
        self.logo_image = ft.Image(src="/logo.png", width=90, height=90, fit="contain")
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, color="#E11D48", size=14)
        self.status_text = ft.Text("غير متصل / Disconnected", color="#E11D48", weight=ft.FontWeight.W_600)
        self.queue_text = ft.Text("الانتظار: 0 / Queue: 0", size=12, color=ft.Colors.WHITE54)
        
        self.wallet_dropdown = ft.Dropdown(
            label="رقم المحفظة / Wallet Number",
            options=[
                ft.dropdown.Option("010_WALLET_1", text="فودافون - 010 (1)"),
                ft.dropdown.Option("010_WALLET_2", text="فودافون - 010 (2)"),
                ft.dropdown.Option("011_WALLET_3", text="اتصالات - 011"),
            ],
            value="010_WALLET_1",
            width=310,
            **self.input_style
        )
        
        self.ip_field = ft.TextField(
            label="عنوان الحاسوب (Desktop IP)", 
            value=WEBSOCKET_HOST, 
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            **self.input_style
        )
        self.port_field = ft.TextField(
            label="المنفذ (Port)", 
            value=str(WEBSOCKET_PORT), 
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            **self.input_style
        )
        
        self.connect_btn = ft.ElevatedButton(
            "اتصال بالديسكتوب / Connect to Desktop", 
            on_click=self.reconnect, 
            icon=ft.Icons.WIFI,
            color=ft.Colors.WHITE,
            bgcolor="#0F3C6D",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            width=310,
            height=45
        )

        # عناصر المزامنة السحابية المباشرة (Cloud Sync UI)
        self.direct_sync_switch = ft.Switch(
            label="مزامنة مباشرة مع السيرفر / Direct Sync",
            value=self.stored_direct_sync,
            active_color="#1E8F8B",
            on_change=self.toggle_direct_sync
        )

        self.server_url_field = ft.TextField(
            label="رابط السيرفر / Server URL",
            value=self.stored_server_url,
            width=310,
            **self.input_style
        )

        self.license_key_field = ft.TextField(
            label="مفتاح الترخيص / License Key",
            value=self.stored_license_key,
            password=True,
            can_reveal_password=True,
            width=310,
            **self.input_style
        )

        self.cloud_test_status = ft.Text("", size=13, weight=ft.FontWeight.W_500)

        self.save_test_btn = ft.ElevatedButton(
            "حفظ واختبار الاتصال / Save & Test Sync",
            on_click=self.save_and_test_cloud,
            icon=ft.Icons.CLOUD_SYNC,
            color=ft.Colors.WHITE,
            bgcolor="#1E8F8B",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            width=310,
            height=45
        )

        # تجميع العناصر في كروت أنيقة لتبدو الواجهة احترافية
        desktop_card = ft.Container(
            content=ft.Column([
                ft.Text("الاتصال بالحاسوب (Desktop Connection)", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([self.ip_field, self.port_field], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                self.connect_btn
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            border_radius=15,
            bgcolor="#0E1321",
            border=ft.border.all(1, ft.Colors.WHITE10)
        )

        cloud_card = ft.Container(
            content=ft.Column([
                ft.Text("المزامنة السحابية (Cloud Server Sync)", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.direct_sync_switch,
                self.server_url_field,
                self.license_key_field,
                self.cloud_test_status,
                self.save_test_btn
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            border_radius=15,
            bgcolor="#0E1321",
            border=ft.border.all(1, ft.Colors.WHITE10)
        )

        self.content = ft.Column(
            controls=[
                ft.Container(content=self.logo_image, margin=ft.Margin(left=0, top=10, right=0, bottom=5)),
                ft.Text("دفتر كاش - Daftar Cash", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([self.status_icon, self.status_text, self.queue_text], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                ft.Text("إعداد المحفظة / Wallet Config", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.wallet_dropdown,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                desktop_card,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                cloud_card,
                
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text("برنامج دفتر كاش يعمل في الخلفية لمراقبة الرسائل المباشرة.\nDaftar Cash is running in background.", text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE38, size=11),
                ft.Container(height=20)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        )
        
        # ربط الـ Callbacks للـ Broadcaster
        self.broadcaster._on_connected = self.on_connected
        self.broadcaster._on_disconnected = self.on_disconnected

    def reconnect(self, e):
        self.status_text.value = "جاري الاتصال... / Connecting..."
        self.status_text.color = "#F59E0B"
        self.status_icon.color = "#F59E0B"
        self.flet_page.update()
        
        # تحديث الإعدادات وإعادة تشغيل الـ Broadcaster
        self.broadcaster.stop()
        self.broadcaster._host = self.ip_field.value
        self.broadcaster._port = int(self.port_field.value)
        self.broadcaster._uri = f"ws://{self.broadcaster._host}:{self.broadcaster._port}"
        self.broadcaster.start()

    def toggle_direct_sync(self, e):
        # حفظ خيار التفعيل
        val = "1" if self.direct_sync_switch.value else "0"
        self.db.set_setting("direct_sync", val)
        logger.info(f"Direct sync toggled: {self.direct_sync_switch.value}")

    def save_and_test_cloud(self, e):
        url = self.server_url_field.value.strip()
        key = self.license_key_field.value.strip()

        # إزالة الشرطة المائلة الأخيرة إن وجدت لتوحيد الرابط
        if url.endswith("/"):
            url = url[:-1]

        self.db.set_setting("server_url", url)
        self.db.set_setting("license_key", key)

        self.cloud_test_status.value = "جاري التحقق من الترخيص... / Validating..."
        self.cloud_test_status.color = "#F59E0B"
        self.save_test_btn.disabled = True
        self.flet_page.update()

        try:
            # التحقق عبر السيرفر
            api_url = f"{url}/validate-license/"
            logger.info(f"Testing license validation to: {api_url}")
            response = httpx.post(api_url, json={"key": key, "mac_address": "mobile-client"}, timeout=8.0)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    self.cloud_test_status.value = "✅ تم التحقق بنجاح والاتصال مستقر!"
                    self.cloud_test_status.color = "#10B981"
                else:
                    msg = data.get("message", "خطأ في التحقق من الترخيص")
                    self.cloud_test_status.value = f"❌ فشل: {msg}"
                    self.cloud_test_status.color = "#E11D48"
            else:
                self.cloud_test_status.value = f"❌ خطأ في السيرفر: رمز الاستجابة {response.status_code}"
                self.cloud_test_status.color = "#E11D48"
        except Exception as err:
            logger.error(f"License validation exception: {err}")
            self.cloud_test_status.value = f"❌ فشل الاتصال بالسيرفر: {str(err)[:50]}"
            self.cloud_test_status.color = "#E11D48"

        self.save_test_btn.disabled = False
        self.flet_page.update()

    def on_connected(self):
        self.status_text.value = "متصل بالديسكتوب / Connected to Desktop"
        self.status_text.color = "#10B981"
        self.status_icon.color = "#10B981"
        self.flet_page.update()

    def on_disconnected(self):
        self.status_text.value = "غير متصل بالديسكتوب / Disconnected"
        self.status_text.color = "#E11D48"
        self.status_icon.color = "#E11D48"
        self.flet_page.update()
