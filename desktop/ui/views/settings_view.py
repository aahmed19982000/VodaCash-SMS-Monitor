# desktop/ui/views/settings_view.py
import socket
import flet as ft

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
            "instapay": "انستاباي (InstaPay)",
            "bank": "حساب بنكي (Bank Account)"
        }
        self.balance_inputs = {}

        # إعدادات التنبيهات من قاعدة البيانات
        notif_val = self.db.get_setting("notifications_enabled", "true") == "true" if self.db else True
        sound_val = self.db.get_setting("sound_enabled", "true") == "true" if self.db else True

        self.switch_notifications = ft.Switch(
            label="تفعيل إشعارات سطح المكتب (Enable Desktop Notifications)",
            value=notif_val,
            on_change=self.on_notifications_change
        )
        self.switch_sound = ft.Switch(
            label="تفعيل صوت التنبيه (Enable Notification Sound)",
            value=sound_val,
            on_change=self.on_sound_change
        )

        # جلب الـ IP المحلي
        self.local_ips = self.get_local_ips()

        ips_list = ft.ListView(spacing=10, expand=True)
        for ip in self.local_ips:
            ips_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.WIFI, color=ft.Colors.BLUE_400),
                    title=ft.Text(f"Wi-Fi / LAN IP: {ip}", weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text("أدخل هذا الرقم في إعدادات التطبيق على الموبايل."),
                )
            )

        # Dialog for confirmation
        self.confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("تأكيد تصفير العمليات والنشاط"),
            content=ft.Text("هل أنت متأكد من رغبتك في تصفير جميع العمليات والنشاط؟ سيتم حذف كافة العمليات والبيانات من قاعدة بيانات الكمبيوتر والموبايل بشكل نهائي ولا يمكن التراجع عن ذلك."),
            actions=[
                ft.TextButton("نعم، تصفير", on_click=self.confirm_clear_data, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
                ft.TextButton("إلغاء", on_click=self.close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("Connection Info & Settings", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                ft.Text(
                    "لتوصيل تطبيق الموبايل بسطح المكتب، قم بفتح شاشة الإعدادات في الموبايل وأدخل أحد عناوين الـ IP التالية:",
                    size=16,
                    color=ft.Colors.WHITE70
                ),
                
                ft.Container(
                    content=ips_list,
                    height=180,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                    padding=10,
                    margin=ft.Margin(left=0, top=10, right=0, bottom=10)
                ),

                ft.Text("ملاحظة:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                ft.Text("• إذا كنت تستخدم كابل USB مع (adb reverse tcp:8765 tcp:8765)، فاختر وضع USB في الموبايل ليتم الاتصال عبر 127.0.0.1", color=ft.Colors.WHITE54),
                ft.Text("• إذا كنت تستخدم Wi-Fi، أدخل أحد عناوين الـ IP المعروضة هنا وشكّل استثناء لـ port 8765 في جدار الحماية الخاص بويندوز.", color=ft.Colors.WHITE54),
                
                ft.Divider(height=30, color=ft.Colors.WHITE24),

                # قسم إعدادات الإشعارات
                ft.Text("إعدادات التنبيهات (Notification Settings)", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                ft.Text("تحكم في كيفية تنبيهك عند استلام عمليات جديدة على الكمبيوتر.", color=ft.Colors.WHITE54),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.switch_notifications,
                            self.switch_sound,
                        ],
                        spacing=15,
                    ),
                    margin=ft.Margin(left=0, top=10, right=0, bottom=20)
                ),
                
                ft.Divider(height=30, color=ft.Colors.WHITE24),

                # قسم تعديل الأرصدة
                ft.Text("تعديل أرصدة الحسابات والمحافظ (Wallet & Account Balances)", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                ft.Text("يمكنك إدخال الرصيد الحالي الفعلي لأي محفظة أو حساب (مثال: انستا باي)، وسيقوم التطبيق بحساب الرصيد تلقائياً بناءً على المعاملات اللاحقة.", color=ft.Colors.WHITE54),
                self.build_balances_section(),
                
                ft.Divider(height=30, color=ft.Colors.WHITE24),
                
                # قسم إجراءات النظام
                ft.Text("إجراءات النظام (System Actions)", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                ft.Text("استخدم هذا الزر لحذف كافة السجلات وتصفير الحساب لتبدأ من جديد.", color=ft.Colors.WHITE54),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "تصفير السجل والنشاط بالكامل",
                                icon=ft.Icons.DELETE_FOREVER,
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.RED_700,
                                on_click=self.show_clear_dialog,
                            )
                        ]
                    ),
                    margin=ft.Margin(left=0, top=10, right=0, bottom=10)
                )
            ]
        )

    def show_clear_dialog(self, e):
        self.flet_page.dialog = self.confirm_dialog
        self.confirm_dialog.open = True
        self.flet_page.update()

    def close_dialog(self, e):
        self.confirm_dialog.open = False
        self.flet_page.update()

    def confirm_clear_data(self, e):
        self.confirm_dialog.open = False
        
        # 1. Clear Desktop DB
        db_cleared = False
        if self.db:
            db_cleared = self.db.clear_database()
            
        # 2. Broadcast Reset command to mobile clients
        if self.server:
            import asyncio
            from shared.protocol import make_reset_activity
            try:
                # Send clear message over websocket
                asyncio.create_task(self.server._broadcast(make_reset_activity()))
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

    def build_balances_section(self):
        kpi = self.db.get_kpi_summary() if self.db else {}
        wallet_balances = kpi.get("wallet_balances", {})
        
        controls = []
        for w_id, w_name in self.wallet_names.items():
            current_bal = wallet_balances.get(w_id, 0.0)
            
            tf = ft.TextField(
                value=f"{current_bal:.2f}",
                width=120,
                text_align=ft.TextAlign.RIGHT,
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=10,
                height=40,
                text_size=14,
            )
            self.balance_inputs[w_id] = tf
            
            controls.append(
                ft.Row(
                    controls=[
                        ft.Text(w_name, weight=ft.FontWeight.W_500, expand=True, size=15),
                        tf,
                        ft.Text(" EGP", size=14, color=ft.Colors.WHITE70),
                        ft.IconButton(
                            icon=ft.Icons.SAVE_ROUNDED,
                            icon_color=ft.Colors.BLUE_400,
                            tooltip="تحديث الرصيد / Update Balance",
                            on_click=lambda e, wallet=w_id: self.update_wallet_balance(wallet)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
            
        return ft.Container(
            content=ft.Column(controls=controls, spacing=10),
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=10,
            padding=15,
            bgcolor=ft.Colors.BLACK12,
            margin=ft.Margin(0, 10, 0, 20)
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

    def update_data(self):
        """تحديث قيم الأرصدة المعروضة من قاعدة البيانات"""
        if not self.db:
            return
        kpi = self.db.get_kpi_summary()
        wallet_balances = kpi.get("wallet_balances", {})
        for w_id, tf in self.balance_inputs.items():
            current_bal = wallet_balances.get(w_id, 0.0)
            tf.value = f"{current_bal:.2f}"
        self.flet_page.update()
