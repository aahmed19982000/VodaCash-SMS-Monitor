# mobile/ui/app.py
import flet as ft
from mobile.db.database import MobileDatabase
from mobile.broadcaster import Broadcaster
from shared.config import WEBSOCKET_HOST, WEBSOCKET_PORT

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

        # UI Elements
        self.logo_image = ft.Image(src="/logo.png", width=120, height=120, fit="contain")
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
            "اتصال / Connect", 
            on_click=self.reconnect, 
            icon=ft.Icons.WIFI,
            color=ft.Colors.WHITE,
            bgcolor="#0F3C6D",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            width=310,
            height=45
        )

        self.content = ft.Column(
            controls=[
                ft.Container(content=self.logo_image, margin=ft.Margin(left=0, top=20, right=0, bottom=10)),
                ft.Text("دفتر كاش - Daftar Cash", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([self.status_icon, self.status_text, self.queue_text], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                ft.Text("إعداد المحفظة / Wallet Config", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.wallet_dropdown,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                ft.Text("إعدادات الاتصال / Connection Settings", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([self.ip_field, self.port_field], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Container(height=5),
                self.connect_btn,
                
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.Text("برنامج دفتر كاش يعمل في الخلفية لمراقبة الرسائل المباشرة.\nDaftar Cash is running in background.", text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE38, size=11)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # ربط الـ Callbacks
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

    def on_connected(self):
        self.status_text.value = "متصل / Connected"
        self.status_text.color = "#10B981"
        self.status_icon.color = "#10B981"
        self.flet_page.update()

    def on_disconnected(self):
        self.status_text.value = "غير متصل / Disconnected"
        self.status_text.color = "#E11D48"
        self.status_icon.color = "#E11D48"
        self.flet_page.update()
