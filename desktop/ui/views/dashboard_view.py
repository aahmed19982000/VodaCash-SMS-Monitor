# desktop/ui/views/dashboard_view.py
import flet as ft
from desktop.db.database import DesktopDatabase

class DashboardView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        # KPI Controls
        self.balance_text = ft.Text("0.00 EGP", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.income_text = ft.Text("0.00 EGP", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.expenses_text = ft.Text("0.00 EGP", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.count_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)

        # Recent Activity List
        self.activity_list = ft.ListView(expand=True, spacing=10)

        self.content = ft.Column(
            controls=[
                ft.Text("Dashboard", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                # KPI Cards Row
                ft.Row(
                    controls=[
                        self._build_kpi_card("Current Balance", self.balance_text, ft.Icons.ACCOUNT_BALANCE_WALLET, ft.Colors.BLUE_GREY_900),
                        self._build_kpi_card("Monthly Income", self.income_text, ft.Icons.ARROW_DOWNWARD, ft.Colors.BLUE_GREY_900),
                        self._build_kpi_card("Monthly Expenses", self.expenses_text, ft.Icons.ARROW_UPWARD, ft.Colors.BLUE_GREY_900),
                        self._build_kpi_card("Total TXs", self.count_text, ft.Icons.LIST_ALT, ft.Colors.BLUE_GREY_900),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                
                ft.Divider(height=30, color=ft.Colors.WHITE24),
                
                ft.Text("Recent Activity (Live)", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.activity_list,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                    padding=10,
                )
            ]
        )

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, bg_color: str):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, color=ft.Colors.WHITE54), ft.Text(title, color=ft.Colors.WHITE54)], alignment=ft.MainAxisAlignment.CENTER),
                    text_control
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=220,
            height=120,
            bgcolor=bg_color,
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.BLACK38)
        )

    def update_data(self):
        """يُستدعى لتحديث البيانات من قاعدة البيانات"""
        kpi = self.db.get_kpi_summary()
        self.balance_text.value = f"{kpi['current_balance']:,.2f} EGP"
        self.income_text.value = f"+{kpi['income']:,.2f} EGP"
        self.expenses_text.value = f"-{kpi['expenses']:,.2f} EGP"
        self.count_text.value = str(kpi['transactions_count'])

        # تحديث قائمة آخر العمليات
        recent_txs = self.db.get_all_transactions()[:15] # آخر 15
        self.activity_list.controls.clear()
        
        if not recent_txs:
            self.activity_list.controls.append(ft.Text("No recent transactions.", color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER))
        else:
            for tx in recent_txs:
                icon_color = ft.Colors.GREEN if tx.type.value == "RECEIVED" else ft.Colors.RED if tx.type.value in ["SENT", "PURCHASE", "BILL"] else ft.Colors.BLUE
                icon_name = ft.Icons.CALL_RECEIVED if tx.type.value == "RECEIVED" else ft.Icons.CALL_MADE
                
                self.activity_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(icon_name, color=icon_color),
                        title=ft.Text(f"{tx.type.value} — {tx.amount} EGP", weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"Counterpart: {tx.counterpart} | Date: {tx.sms_timestamp.strftime('%Y-%m-%d %H:%M')} | Bal: {tx.balance_after}"),
                    )
                )
        
        self.flet_page.update()

