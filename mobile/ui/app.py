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

        # UI Elements
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.RED)
        self.status_text = ft.Text("Disconnected", color=ft.Colors.RED)
        self.queue_text = ft.Text("Queue: 0", size=12, color=ft.Colors.WHITE54)
        
        self.wallet_dropdown = ft.Dropdown(
            label="Wallet Number",
            options=[
                ft.dropdown.Option("010_WALLET_1", text="Vodafone - 010 (1)"),
                ft.dropdown.Option("010_WALLET_2", text="Vodafone - 010 (2)"),
                ft.dropdown.Option("011_WALLET_3", text="Etisalat - 011"),
            ],
            value="010_WALLET_1",
            width=310,
        )
        
        self.ip_field = ft.TextField(
            label="Desktop IP", 
            value=WEBSOCKET_HOST, 
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        self.port_field = ft.TextField(
            label="Port", 
            value=str(WEBSOCKET_PORT), 
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.connect_btn = ft.ElevatedButton("Connect", on_click=self.reconnect, icon=ft.Icons.WIFI)

        self.content = ft.Column(
            controls=[
                ft.Row([self.status_icon, self.status_text, self.queue_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                ft.Text("Wallet Configuration", size=20, weight=ft.FontWeight.BOLD),
                self.wallet_dropdown,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                ft.Text("Connection Settings", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([self.ip_field, self.port_field], alignment=ft.MainAxisAlignment.CENTER),
                self.connect_btn,
                
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Text("VodaCash Monitor is running in the background.", text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE54)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # ربط الـ Callbacks
        self.broadcaster._on_connected = self.on_connected
        self.broadcaster._on_disconnected = self.on_disconnected

    def reconnect(self, e):
        self.status_text.value = "Connecting..."
        self.status_text.color = ft.Colors.AMBER
        self.status_icon.color = ft.Colors.AMBER
        self.flet_page.update()
        
        # تحديث الإعدادات وإعادة تشغيل الـ Broadcaster
        self.broadcaster.stop()
        self.broadcaster._host = self.ip_field.value
        self.broadcaster._port = int(self.port_field.value)
        self.broadcaster._uri = f"ws://{self.broadcaster._host}:{self.broadcaster._port}"
        self.broadcaster.start()

    def on_connected(self):
        self.status_text.value = "Connected"
        self.status_text.color = ft.Colors.GREEN
        self.status_icon.color = ft.Colors.GREEN
        self.flet_page.update()

    def on_disconnected(self):
        self.status_text.value = "Disconnected"
        self.status_text.color = ft.Colors.RED
        self.status_icon.color = ft.Colors.RED
        self.flet_page.update()
