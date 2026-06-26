# desktop/ui/views/settings_view.py
import socket
import flet as ft
from desktop.utils.licensing import get_mac_address

class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, db=None, server=None, on_clear_success=None):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.server = server
        self.on_clear_success = on_clear_success
        self.expand = True
        self.padding = 20

        self.wallet_names = {
            "vodafone_cash": "فودافون كاش (Vodafone Cash)",
            "orange_cash": "أورنج كاش (Orange Cash)",
            "etisalat_cash": "اتصالات كاش (Etisalat Cash)",
            "we_pay": "وي باي (WE Pay)",
            "bank": "حساب بنكي / انستاباي (Bank / InstaPay)"
        }
        self.balance_inputs = {}

        # Consistent Input styling helper
        self.input_style = {
            "border_radius": 10,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": ft.Colors.BLUE_ACCENT,
            "filled": True
        }

        # إعدادات التنبيهات من قاعدة البيانات
        notif_val = self.db.get_setting("notifications_enabled", "true") == "true" if self.db else True
        sound_val = self.db.get_setting("sound_enabled", "true") == "true" if self.db else True

        self.switch_notifications = ft.Switch(
            label="تفعيل إشعارات سطح المكتب (Enable Desktop Notifications)",
            value=notif_val,
            on_change=self.on_notifications_change,
            active_color=ft.Colors.BLUE_ACCENT,
            label_text_style=ft.TextStyle(size=13, color=ft.Colors.WHITE)
        )
        self.switch_sound = ft.Switch(
            label="تفعيل صوت التنبيه (Enable Notification Sound)",
            value=sound_val,
            on_change=self.on_sound_change,
            active_color=ft.Colors.BLUE_ACCENT,
            label_text_style=ft.TextStyle(size=13, color=ft.Colors.WHITE)
        )
        
        track_instapay_val = self.db.get_setting("track_instapay", "true") == "true" if self.db else True
        self.switch_track_instapay = ft.Switch(
            label="تتبع عمليات انستا باي (Track InstaPay)",
            value=track_instapay_val,
            on_change=self.on_track_instapay_change,
            active_color=ft.Colors.BLUE_ACCENT,
            label_text_style=ft.TextStyle(size=13, color=ft.Colors.WHITE)
        )

        # جلب الـ IP المحلي
        self.local_ips = self.get_local_ips()

        ips_list = ft.Row(wrap=True, spacing=15)
        for ip in self.local_ips:
            ips_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(ft.Icons.WIFI, color=ft.Colors.BLUE_400, size=22),
                                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_400),
                                padding=10,
                                border_radius=10,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(f"Wi-Fi / LAN IP", size=11, color=ft.Colors.WHITE54),
                                    ft.Text(ip, size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, selectable=True),
                                ],
                                spacing=2,
                                tight=True
                            )
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    bgcolor="#0B0F19",
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.BLUE_400)),
                    border_radius=12,
                    padding=12,
                    width=250,
                    shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK))
                )
            )

        # Dialog for confirmation (custom overlay style to fix Flet click issues)
        self.confirm_dialog = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("تأكيد تصفير العمليات والنشاط / Reset Confirm", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Text("هل أنت متأكد من رغبتك في تصفير جميع العمليات والنشاط؟ سيتم حذف كافة العمليات والبيانات من قاعدة بيانات الكمبيوتر والموبايل بشكل نهائي ولا يمكن التراجع عن ذلك.\n\nAre you sure you want to reset all transactions? This action is permanent and cannot be undone.", size=13, color=ft.Colors.WHITE70),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("نعم، تصفير / Yes, Reset", on_click=self.confirm_clear_data, bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
                                ft.TextButton("إلغاء / Cancel", on_click=self.close_dialog, style=ft.ButtonStyle(color=ft.Colors.WHITE54)),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            spacing=10,
                        )
                    ],
                    tight=True,
                    spacing=12,
                ),
                bgcolor="#0B0F19",
                border_radius=18,
                padding=20,
                width=500,
                border=ft.Border.all(1, ft.Colors.WHITE10),
            ),
            alignment=ft.alignment.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            left=0,
            top=0,
            right=0,
            bottom=0,
        )

        # Connection & Network Info Panel
        self.ip_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "عناوين الاتصال (Connection IPs)",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_200
                    ),
                    ft.Text(
                        "لتوصيل تطبيق الموبايل بسطح المكتب، قم بفتح شاشة الإعدادات في الموبايل وأدخل أحد عناوين الـ IP التالية:",
                        size=13,
                        color=ft.Colors.WHITE70
                    ),
                    ft.Container(height=5),
                    ips_list,
                    ft.Container(height=5),
                    ft.Text("ملاحظات هامة / Important Notes:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400, size=12),
                    ft.Text("• إذا كنت تستخدم كابل USB مع (adb reverse tcp:8765 tcp:8765)، فاختر وضع USB في الموبايل ليتم الاتصال عبر 127.0.0.1", color=ft.Colors.WHITE54, size=12),
                    ft.Text("• إذا كنت تستخدم Wi-Fi، أدخل أحد عناوين الـ IP المعروضة هنا وشكّل استثناء لـ port 8765 في جدار الحماية الخاص بويندوز.", color=ft.Colors.WHITE54, size=12),
                ],
                spacing=8
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )

        # Notification Settings Panel
        self.notif_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("إعدادات التنبيهات (Notification Settings)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                    ft.Text("تحكم في كيفية تنبيهك عند استلام عمليات جديدة على الكمبيوتر.", color=ft.Colors.WHITE54, size=13),
                    ft.Container(height=5),
                    self.switch_notifications,
                    self.switch_sound,
                    self.switch_track_instapay,
                ],
                spacing=10
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )

        # System Actions Panel
        self.system_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("إجراءات النظام (System Actions)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                    ft.Text("استخدم هذا الزر لحذف كافة السجلات وتصفير الحساب لتبدأ من جديد.", color=ft.Colors.WHITE54, size=13),
                    ft.Container(height=5),
                    ft.ElevatedButton(
                        "تصفير السجل والنشاط بالكامل",
                        icon=ft.Icons.DELETE_FOREVER,
                        color=ft.Colors.WHITE,
                        bgcolor=ft.Colors.RED_700,
                        on_click=self.show_clear_dialog,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(20, 15, 20, 15)
                        )
                    )
                ],
                spacing=8
            ),
            gradient=ft.LinearGradient(
                colors=["#3B0712", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.RED_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )

        # Title Row
        self.title_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.SETTINGS_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                ft.Text("Settings & Connection / الإعدادات والاتصال", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                self.title_row,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                self.ip_panel,
                self.notif_panel,
                self.build_balances_section(),
                self.build_fees_section(),
                self.build_license_section(),
                self.system_panel
            ]
        )

    def build_license_section(self):
        mac = get_mac_address()

        # Backend Type Dropdown
        current_backend = self.db.get_setting("license_backend", "MOCK")
        
        self.backend_type_dropdown = ft.Dropdown(
            label="نوع خادم الترخيص (License Server Type)",
            value=current_backend,
            options=[
                ft.dropdown.Option("MOCK", "نظام تجريبي محلي (Offline Mock)"),
                ft.dropdown.Option("SUPABASE", "خادم سحابي Supabase"),
                ft.dropdown.Option("DJANGO", "خادم ويب Django مخصص"),
            ],
            width=500,
            on_select=self.on_backend_change,
            **self.input_style
        )

        self.supabase_url_input = ft.TextField(
            label="Supabase Project URL (رابط المشروع السحابي)",
            value=self.db.get_setting("supabase_url", ""),
            width=500,
            text_size=13,
            **self.input_style
        )
        
        self.supabase_key_input = ft.TextField(
            label="Supabase Anon Key (المفتاح السحابي)",
            value=self.db.get_setting("supabase_key", ""),
            width=500,
            text_size=13,
            password=True,
            can_reveal_password=True,
            **self.input_style
        )

        self.django_url_input = ft.TextField(
            label="Django API Base URL (رابط خادم ديجانجو)",
            value=self.db.get_setting("django_api_url", "http://localhost:8000/api"),
            width=500,
            text_size=13,
            **self.input_style
        )

        # Containers for conditional settings
        self.supabase_settings_container = ft.Column(
            controls=[
                ft.Text("إعدادات الاتصال بـ Supabase:", size=13, weight=ft.FontWeight.BOLD),
                self.supabase_url_input,
                self.supabase_key_input,
            ],
            spacing=10,
            visible=(current_backend == "SUPABASE")
        )

        self.django_settings_container = ft.Column(
            controls=[
                ft.Text("إعدادات الاتصال بـ Django:", size=13, weight=ft.FontWeight.BOLD),
                self.django_url_input,
            ],
            spacing=10,
            visible=(current_backend == "DJANGO")
        )

        self.license_info_text = ft.Text(
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE
        )

        self.deactivate_btn = ft.ElevatedButton(
            "تسجيل الخروج وإلغاء تفعيل الترخيص / Logout & Deactivate",
            icon=ft.Icons.LOGOUT,
            bgcolor=ft.Colors.RED_900,
            color=ft.Colors.WHITE,
            on_click=self.on_deactivate_license,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )

        # Update initial values
        lic_key = self.db.get_setting("license_key", "")
        lic_expiry = self.db.get_setting("license_expiry", "")
        lic_status = self.db.get_setting("license_status", "")
        
        if lic_key:
            self.license_info_text.value = (
                f"🔑 كود التفعيل: {lic_key}\n"
                f"📅 تاريخ الانتهاء: {lic_expiry}\n"
                f"🟢 الحالة: {lic_status}"
            )
            self.deactivate_btn.visible = True
        else:
            self.license_info_text.value = "❌ لا يوجد كود تفعيل نشط حالياً."
            self.deactivate_btn.visible = False

        license_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "نظام الترخيص والاشتراك (Subscription & Licensing System)",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_200
                    ),
                    ft.Text(
                        f"معرف الجهاز الفريد (MAC Address): {mac}",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_400,
                        selectable=True
                    ),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    self.backend_type_dropdown,
                    ft.Container(height=5),
                    self.supabase_settings_container,
                    self.django_settings_container,
                    ft.Container(height=5),
                    ft.ElevatedButton(
                        "حفظ إعدادات خادم الترخيص / Save Settings",
                        icon=ft.Icons.SAVE,
                        on_click=self.on_save_licensing_settings,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
                    ),
                    ft.Divider(height=15, color=ft.Colors.WHITE10),
                    # License Status
                    ft.Text("حالة الترخيص الحالية (License Info):", size=13, weight=ft.FontWeight.BOLD),
                    self.license_info_text,
                    self.deactivate_btn
                ],
                spacing=12
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )
        return license_panel

    def on_backend_change(self, e):
        backend = self.backend_type_dropdown.value
        self.supabase_settings_container.visible = (backend == "SUPABASE")
        self.django_settings_container.visible = (backend == "DJANGO")
        self.flet_page.update()

    def on_save_licensing_settings(self, e):
        backend = self.backend_type_dropdown.value
        self.db.set_setting("license_backend", backend)
        
        if backend == "SUPABASE":
            url = self.supabase_url_input.value.strip()
            key = self.supabase_key_input.value.strip()
            self.db.set_setting("supabase_url", url)
            self.db.set_setting("supabase_key", key)
        elif backend == "DJANGO":
            django_url = self.django_url_input.value.strip()
            self.db.set_setting("django_api_url", django_url)
            
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text("✅ تم حفظ إعدادات خادم الترخيص بنجاح.", size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.GREEN_800
        )
        self.flet_page.snack_bar.open = True
        self.update_data()

    def on_save_supabase_settings(self, e):
        # Fallback method in case it is called
        self.on_save_licensing_settings(e)


    def on_deactivate_license(self, e):
        self.db.set_setting("license_key", "")
        self.db.set_setting("license_expiry", "")
        self.db.set_setting("license_status", "EXPIRED")
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text("ℹ تم تسجيل الخروج وإلغاء تفعيل الترخيص محلياً. يرجى إعادة تشغيل التطبيق.", size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.BLUE_800
        )
        self.flet_page.snack_bar.open = True
        self.update_data()
        
        # Redirection if desktop app has reload capability (we will handle redirection in app.py)
        if hasattr(self.flet_page, "on_license_deactivated"):
            self.flet_page.on_license_deactivated()

    def show_clear_dialog(self, e):

        self.flet_page.show_dialog_overlay(self.confirm_dialog)

    def close_dialog(self, e):
        self.flet_page.close_dialog_overlay(self.confirm_dialog)

    def confirm_clear_data(self, e):
        self.flet_page.close_dialog_overlay(self.confirm_dialog)
        
        # 1. Clear Desktop DB
        db_cleared = False
        if self.db:
            db_cleared = self.db.clear_database()
            
        # 2. Broadcast Reset command to mobile clients
        if self.server:
            from shared.protocol import make_reset_activity
            try:
                # Send clear message over websocket thread-safely
                self.server.broadcast_threadsafe(make_reset_activity())
            except Exception as ex:
                print(f"Failed to broadcast reset message: {ex}")
                
        # 3. Show confirmation feedback (Snackbar)
        if db_cleared:
            msg = "تم تصفير جميع العمليات وقاعدة البيانات بنجاح وإرسال أمر إعادة التعيين للهواتف المتصلة!"
        else:
            msg = "تم إرسال أمر إعادة التعيين للهواتف المتصلة، ولكن حدث خطأ أثناء تصفير قاعدة بيانات الكمبيوتر."
            
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.GREEN_700 if db_cleared else ft.Colors.ORANGE_700,
        )
        self.flet_page.snack_bar.open = True
        
        # 4. Refresh Desktop views if callback registered
        if self.on_clear_success:
            try:
                self.on_clear_success()
            except Exception as ex:
                print(f"Error calling on_clear_success callback: {ex}")
                
        self.flet_page.update()

    def get_local_ips(self):
        ips = []
        try:
            host_name = socket.gethostname()
            host_ips = socket.gethostbyname_ex(host_name)[2]
            for ip in host_ips:
                if not ip.startswith("127."):
                    ips.append(ip)
            
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            active_ip = s.getsockname()[0]
            s.close()
            
            if active_ip not in ips and not active_ip.startswith("127."):
                ips.insert(0, active_ip)
                
        except Exception:
            pass
            
        if not ips:
            ips.append("غير قادر على تحديد الـ IP التلقائي. افحص الشبكة يدوياً.")
            
        return ips

    def on_notifications_change(self, e):
        val = "true" if self.switch_notifications.value else "false"
        if self.db:
            self.db.set_setting("notifications_enabled", val)
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text("تم حفظ إعدادات الإشعارات بنجاح!", size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.BLUE_700,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    def on_sound_change(self, e):
        val = "true" if self.switch_sound.value else "false"
        if self.db:
            self.db.set_setting("sound_enabled", val)
        
        # تشغيل صوت تجريبي سريع إذا تم تفعيله للتو
        if self.switch_sound.value:
            try:
                import winsound
                import platform
                if platform.system() == "Windows":
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass

        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text("تم حفظ إعدادات صوت التنبيه بنجاح!", size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.BLUE_700,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    def on_track_instapay_change(self, e):
        val = "true" if self.switch_track_instapay.value else "false"
        if self.db:
            self.db.set_setting("track_instapay", val)
            
        # Refresh current settings view to immediately update layout
        try:
            self.update_data()
        except Exception as ex:
            print(f"Error updating settings UI: {ex}")

        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text("تم حفظ إعدادات تتبع انستا باي بنجاح!", size=16, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.BLUE_700,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    def build_balances_section(self):
        kpi = self.db.get_kpi_summary() if self.db else {}
        wallet_balances = kpi.get("wallet_balances", {})
        
        controls = []
        track_instapay = self.db.get_setting("track_instapay", "true") == "true" if self.db else True
        for w_id, w_name in self.wallet_names.items():
            if w_id == "bank" and not track_instapay:
                continue
            current_bal = wallet_balances.get(w_id, 0.0)
            
            tf = ft.TextField(
                value=f"{current_bal:.2f}",
                width=150,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=10,
                height=40,
                text_size=14,
                **self.input_style
            )
            self.balance_inputs[w_id] = tf
            
            # Simple branding colors/icons for wallets
            w_colors = {
                "vodafone_cash": ft.Colors.RED_ACCENT,
                "orange_cash": ft.Colors.ORANGE_ACCENT,
                "etisalat_cash": ft.Colors.GREEN_ACCENT,
                "we_pay": ft.Colors.PURPLE_ACCENT,
                "bank": ft.Colors.CYAN_ACCENT,
            }
            w_color = w_colors.get(w_id, ft.Colors.BLUE_ACCENT)
            
            controls.append(
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    width=8,
                                    height=8,
                                    bgcolor=w_color,
                                    shape=ft.BoxShape.CIRCLE,
                                ),
                                ft.Text(w_name, weight=ft.FontWeight.W_500, size=14, color=ft.Colors.WHITE),
                            ],
                            spacing=8
                        ),
                        ft.Row(
                            controls=[
                                tf,
                                ft.Text(" EGP", size=12, color=ft.Colors.WHITE54),
                                ft.IconButton(
                                    icon=ft.Icons.SAVE_ROUNDED,
                                    icon_color=ft.Colors.BLUE_400,
                                    tooltip="تحديث الرصيد / Update Balance",
                                    on_click=lambda e, wallet=w_id: self.update_wallet_balance(wallet)
                                )
                            ],
                            spacing=5,
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
            
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("تعديل أرصدة الحسابات والمحافظ (Wallet & Account Balances)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                    ft.Text("يمكنك إدخال الرصيد الحالي الفعلي لأي محفظة أو حساب (مثال: انستا باي)، وسيقوم التطبيق بحساب الرصيد تلقائياً بناءً على المعاملات اللاحقة.", color=ft.Colors.WHITE54, size=13),
                    ft.Container(height=5),
                    ft.Column(controls=controls, spacing=12),
                ],
                spacing=10
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )

    def update_wallet_balance(self, wallet_id):
        tf = self.balance_inputs.get(wallet_id)
        if not tf or not self.db:
            return
            
        val_str = tf.value.strip()
        try:
            new_balance = float(val_str)
        except ValueError:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text("الرجاء إدخال رقم صحيح!", size=16, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.RED_700,
            )
            self.flet_page.snack_bar.open = True
            self.flet_page.update()
            return
            
        # احسب صافي التغير في قاعدة البيانات لهذه المحفظة
        net_change = self.db.get_wallet_net_change(wallet_id)
        
        # الرصيد الابتدائي = الرصيد الجديد - صافي التغير
        initial_balance = new_balance - net_change
        
        # حفظ الرصيد الابتدائي كإعداد
        success = self.db.set_setting(f"initial_balance_{wallet_id}", str(initial_balance))
        
        if success:
            msg = f"تم تحديث رصيد محفظة {self.wallet_names[wallet_id]} بنجاح!"
            bg = ft.Colors.GREEN_700
            
            # تحديث شاشات لوحة التحكم
            if self.on_clear_success:
                try:
                    self.on_clear_success()
                except Exception as ex:
                    print(f"Error calling on_clear_success callback: {ex}")
        else:
            msg = "حدث خطأ أثناء حفظ الإعدادات."
            bg = ft.Colors.RED_700
            
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, size=16, weight=ft.FontWeight.BOLD),
            bgcolor=bg,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    def build_fees_section(self):
        self.fee_deposit_inputs = {}
        self.fee_withdraw_inputs = {}
        self.fee_withdraw_min_inputs = {}
        
        controls = []
        track_instapay = self.db.get_setting("track_instapay", "true") == "true" if self.db else True
        for w_id, w_name in self.wallet_names.items():
            if w_id == "bank" and not track_instapay:
                continue
            # Get current values from DB (defaults are 0.0)
            dep_fee = self.db.get_setting(f"fee_deposit_{w_id}", "0.0") if self.db else "0.0"
            wth_fee = self.db.get_setting(f"fee_withdraw_{w_id}", "0.0") if self.db else "0.0"
            wth_min = self.db.get_setting(f"fee_withdraw_min_{w_id}", "0.0") if self.db else "0.0"
            
            tf_dep = ft.TextField(
                value=dep_fee,
                label="الإيداع % (Dep %)",
                width=120,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=10,
                height=45,
                text_size=13,
                **self.input_style
            )
            tf_wth = ft.TextField(
                value=wth_fee,
                label="السحب % (Wth %)",
                width=120,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=10,
                height=45,
                text_size=13,
                **self.input_style
            )
            tf_min = ft.TextField(
                value=wth_min,
                label="الأدنى ج.م (Min EGP)",
                width=120,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=10,
                height=45,
                text_size=13,
                **self.input_style
            )
            
            self.fee_deposit_inputs[w_id] = tf_dep
            self.fee_withdraw_inputs[w_id] = tf_wth
            self.fee_withdraw_min_inputs[w_id] = tf_min
            
            w_colors = {
                "vodafone_cash": ft.Colors.RED_ACCENT,
                "orange_cash": ft.Colors.ORANGE_ACCENT,
                "etisalat_cash": ft.Colors.GREEN_ACCENT,
                "we_pay": ft.Colors.PURPLE_ACCENT,
                "bank": ft.Colors.CYAN_ACCENT,
            }
            w_color = w_colors.get(w_id, ft.Colors.BLUE_ACCENT)

            controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                width=8,
                                                height=8,
                                                bgcolor=w_color,
                                                shape=ft.BoxShape.CIRCLE,
                                            ),
                                            ft.Text(w_name, weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.WHITE),
                                        ],
                                        spacing=8
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.SAVE_ROUNDED,
                                        icon_color=ft.Colors.BLUE_400,
                                        tooltip="حفظ الرسوم / Save Fees",
                                        on_click=lambda e, wallet=w_id: self.update_wallet_fees(wallet)
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Row(
                                controls=[
                                    tf_dep,
                                    tf_wth,
                                    tf_min,
                                ],
                                spacing=15,
                                alignment=ft.MainAxisAlignment.START
                            )
                        ],
                        spacing=5
                    ),
                    padding=ft.Padding(0, 0, 0, 10),
                    border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.WHITE10))
                )
            )
            
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("تحديد أرباح/رسوم السحب والإيداع للمحافظ (Wallet Profit/Fee Settings)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                    ft.Text("حدد نسبة الرسوم (الأرباح التي ستحصل عليها) للإيداع والسحب والحد الأدنى لرسوم السحب لكل محفظة ليتم احتسابها ديناميكياً وعرضها كأرباح لك في التطبيق.", color=ft.Colors.WHITE54, size=13),
                    ft.Container(height=5),
                    ft.Column(controls=controls, spacing=10),
                ],
                spacing=10
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
            border_radius=16,
            padding=20,
            margin=ft.Margin(0, 0, 0, 15)
        )

    def update_wallet_fees(self, wallet_id):
        tf_dep = self.fee_deposit_inputs.get(wallet_id)
        tf_wth = self.fee_withdraw_inputs.get(wallet_id)
        tf_min = self.fee_withdraw_min_inputs.get(wallet_id)
        
        if not tf_dep or not tf_wth or not tf_min or not self.db:
            return
            
        dep_str = tf_dep.value.strip()
        wth_str = tf_wth.value.strip()
        min_str = tf_min.value.strip()
        
        try:
            dep_val = float(dep_str)
            wth_val = float(wth_str)
            min_val = float(min_str)
            if dep_val < 0 or wth_val < 0 or min_val < 0:
                raise ValueError("Values must be positive")
        except ValueError:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text("الرجاء إدخال أرقام موجبة صحيحة!", size=16, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.RED_700,
            )
            self.flet_page.snack_bar.open = True
            self.flet_page.update()
            return
            
        # Save settings to DB
        s1 = self.db.set_setting(f"fee_deposit_{wallet_id}", f"{dep_val:.2f}")
        s2 = self.db.set_setting(f"fee_withdraw_{wallet_id}", f"{wth_val:.2f}")
        s3 = self.db.set_setting(f"fee_withdraw_min_{wallet_id}", f"{min_val:.2f}")
        
        if s1 and s2 and s3:
            msg = f"تم تحديث رسوم محفظة {self.wallet_names[wallet_id]} بنجاح!"
            bg = ft.Colors.GREEN_700
            
            # Notify views to refresh
            if self.on_clear_success:
                try:
                    self.on_clear_success()
                except Exception as ex:
                    print(f"Error calling on_clear_success callback: {ex}")
        else:
            msg = "حدث خطأ أثناء حفظ الإعدادات."
            bg = ft.Colors.RED_700
            
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, size=16, weight=ft.FontWeight.BOLD),
            bgcolor=bg,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    def update_data(self):
        """تحديث قيم الأرصدة والرسوم المعروضة من قاعدة البيانات"""
        if not self.db:
            return
            
        # Rebuild Balances and Fees UI sections to respect track_instapay toggle status instantly
        if hasattr(self, 'balances_container'):
            self.balances_container.content = self.build_balances_section()
        if hasattr(self, 'fees_container'):
            self.fees_container.content = self.build_fees_section()

        # 1. Balances
        kpi = self.db.get_kpi_summary()
        wallet_balances = kpi.get("wallet_balances", {})
        for w_id, tf in self.balance_inputs.items():
            current_bal = wallet_balances.get(w_id, 0.0)
            tf.value = f"{current_bal:.2f}"
            
        # 2. Fees
        if hasattr(self, 'fee_deposit_inputs'):
            for w_id in self.wallet_names.keys():
                dep_fee = self.db.get_setting(f"fee_deposit_{w_id}", "0.0")
                wth_fee = self.db.get_setting(f"fee_withdraw_{w_id}", "0.0")
                wth_min = self.db.get_setting(f"fee_withdraw_min_{w_id}", "0.0")
                
                if w_id in self.fee_deposit_inputs:
                    self.fee_deposit_inputs[w_id].value = dep_fee
                if w_id in self.fee_withdraw_inputs:
                    self.fee_withdraw_inputs[w_id].value = wth_fee
                if w_id in self.fee_withdraw_min_inputs:
                    self.fee_withdraw_min_inputs[w_id].value = wth_min

        # 3. License Info
        if hasattr(self, 'backend_type_dropdown'):
            current_backend = self.db.get_setting("license_backend", "MOCK")
            self.backend_type_dropdown.value = current_backend
            
            url = self.db.get_setting("supabase_url", "")
            key = self.db.get_setting("supabase_key", "")
            self.supabase_url_input.value = url
            self.supabase_key_input.value = key
            
            django_url = self.db.get_setting("django_api_url", "http://localhost:8000/api")
            self.django_url_input.value = django_url
            
            self.supabase_settings_container.visible = (current_backend == "SUPABASE")
            self.django_settings_container.visible = (current_backend == "DJANGO")
            
            lic_key = self.db.get_setting("license_key", "")
            lic_expiry = self.db.get_setting("license_expiry", "")
            lic_status = self.db.get_setting("license_status", "")
            
            if lic_key:
                self.license_info_text.value = (
                    f"🔑 كود التفعيل: {lic_key}\n"
                    f"📅 تاريخ الانتهاء: {lic_expiry}\n"
                    f"🟢 الحالة: {lic_status}"
                )
                self.deactivate_btn.visible = True
            else:
                self.license_info_text.value = "❌ لا يوجد كود تفعيل نشط حالياً."
                self.deactivate_btn.visible = False

        if hasattr(self, 'switch_track_instapay'):
            self.switch_track_instapay.value = self.db.get_setting("track_instapay", "true") == "true"

        self.flet_page.update()

