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
