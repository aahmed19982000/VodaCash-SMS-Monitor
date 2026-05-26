# desktop/ui/views/login_view.py
import flet as ft
from desktop.utils.licensing import LicensingManager, get_mac_address

class LoginView(ft.Container):
    def __init__(self, page: ft.Page, db, on_login_success):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.on_login_success = on_login_success
        self.lic_mgr = LicensingManager(db=self.db)
        
        self.expand = True
        self.alignment = ft.alignment.Alignment.CENTER

        self.bgcolor = "#080C14"
        
        # Styles
        self.input_style = {
            "border_radius": 10,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": "#1E8F8B",
            "filled": True,
            "text_size": 14,
            "label_style": ft.TextStyle(color=ft.Colors.WHITE54)
        }

        self.build_ui()

    def build_ui(self):
        mac = get_mac_address()

        # Logo & App Title
        self.logo_icon = ft.Image(src="/logo.png", width=120, height=120, fit="contain")
        self.app_title = ft.Text("دفتر كاش - Daftar Cash", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.app_sub = ft.Text("نظام تفعيل وإدارة الاشتراكات / Subscription Activation", size=13, color=ft.Colors.WHITE54)

        # MAC display
        self.mac_text = ft.Text(f"معرف الجهاز (MAC Address): {mac}", size=11, weight=ft.FontWeight.BOLD, color="#1E8F8B", selectable=True)

        # --- Account Login Fields ---
        self.username_input = ft.TextField(
            label="اسم المستخدم أو البريد الإلكتروني (Username / Email)",
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
            **self.input_style
        )
        self.password_input = ft.TextField(
            label="كلمة المرور (Password)",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            **self.input_style
        )
        self.login_btn = ft.ElevatedButton(
            "تسجيل الدخول والتفعيل / Login & Activate",
            icon=ft.Icons.LOGIN,
            color=ft.Colors.WHITE,
            bgcolor="#1E8F8B",
            width=350,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=self.on_login_click
        )

        # Error display
        self.error_text = ft.Text("", color=ft.Colors.RED_400, size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        self.success_text = ft.Text("", color=ft.Colors.GREEN_400, size=14, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        self.loading_ring = ft.ProgressRing(visible=False, width=24, height=24)

        # Assemble login card
        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    self.logo_icon,
                    self.app_title,
                    self.app_sub,
                    ft.Container(height=10),
                    self.mac_text,
                    ft.Divider(height=20, color=ft.Colors.WHITE10),
                    
                    self.error_text,
                    self.success_text,
                    
                    self.username_input,
                    self.password_input,
                    ft.Container(height=10),
                    ft.Row([self.login_btn, self.loading_ring], alignment=ft.MainAxisAlignment.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                tight=True
            ),
            width=420,
            bgcolor="#0F172A",
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=18,
            padding=30,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)
            )
        )

    def set_loading(self, loading: bool):
        self.loading_ring.visible = loading
        self.login_btn.disabled = loading
        self.update()

    def on_login_click(self, e):
        username_val = self.username_input.value.strip()
        password_val = self.password_input.value.strip()

        if not username_val or not password_val:
            self.error_text.value = "يرجى إدخال اسم المستخدم وكلمة المرور."
            self.update()
            return

        self.error_text.value = ""
        self.success_text.value = ""
        self.set_loading(True)

        # Open default browser to check/verify subscription status
        try:
            django_url = self.db.get_setting("django_api_url", "http://localhost:8000/api")
            base_url = django_url.split("/api")[0]
            dashboard_url = f"{base_url}/dashboard/"
            self.flet_page.launch_url(dashboard_url)
        except Exception as ex:
            print(f"Error launching browser: {ex}")

        import threading
        def login_license_thread():
            mac = get_mac_address()
            res = self.lic_mgr.login_license(username_val, password_val, mac)
            
            def update_ui():
                self.set_loading(False)
                if res["success"]:
                    lic = res["license"]
                    self.db.set_setting("license_key", lic["key"])
                    self.db.set_setting("license_expiry", lic["expires_at"])
                    self.db.set_setting("license_status", "ACTIVE")
                    
                    self.success_text.value = res["message"]
                    self.update()
                    
                    import time
                    time.sleep(1.5)
                    self.on_login_success()
                else:
                    self.error_text.value = res["message"]
                    self.update()
            
            self.flet_page.run_thread(update_ui)

        threading.Thread(target=login_license_thread, daemon=True).start()
