# desktop/ui/views/settings_view.py
import socket
import flet as ft

class SettingsView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.flet_page = page
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

        self.content = ft.Column(
            controls=[
                ft.Text("Connection Info", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                ft.Text(
                    "لتوصيل تطبيق الموبايل بسطح المكتب، قم بفتح شاشة الإعدادات في الموبايل وأدخل أحد عناوين الـ IP التالية:",
                    size=16,
                    color=ft.Colors.WHITE70
                ),
                
                ft.Container(
                    content=ips_list,
                    height=200,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                    padding=10,
                    margin=ft.Margin(left=0, top=20, right=0, bottom=20)
                ),

                ft.Text("ملاحظة:", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                ft.Text("إذا كنت تستخدم كابل USB مع (adb reverse tcp:8765 tcp:8765)، فاختر وضع USB في الموبايل ليتم الاتصال عبر 127.0.0.1", color=ft.Colors.WHITE54)
            ]
        )

    def get_local_ips(self):
        ips = []
        try:
            # طريقة للحصول على كل واجهات الشبكة
            host_name = socket.gethostname()
            host_ips = socket.gethostbyname_ex(host_name)[2]
            for ip in host_ips:
                if not ip.startswith("127."):
                    ips.append(ip)
            
            # طريقة بديلة في حال لم ترجع الأولى شيء (مثل بعض أنظمة الماك)
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
