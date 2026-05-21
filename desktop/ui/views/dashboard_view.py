# desktop/ui/views/dashboard_view.py
import flet as ft
from desktop.db.database import DesktopDatabase
from shared.config import WALLET_SENDERS

WALLET_STYLING = {
    "vodafone_cash": {
        "name": "Vodafone Cash",
        "name_ar": "فودافون كاش",
        "colors": ["#E60000", "#990000"],
        "icon": ft.Icons.PHONE_ANDROID,
    },
    "orange_cash": {
        "name": "Orange Cash",
        "name_ar": "أورنج كاش",
        "colors": ["#FF6600", "#CC5200"],
        "icon": ft.Icons.MONEY_ROUNDED,
    },
    "etisalat_cash": {
        "name": "Etisalat Cash",
        "name_ar": "اتصالات كاش",
        "colors": ["#78BE20", "#5A8F18"],
        "icon": ft.Icons.PHONELINK_RING,
    },
    "we_pay": {
        "name": "WE Pay",
        "name_ar": "وي باي",
        "colors": ["#512D6D", "#351C49"],
        "icon": ft.Icons.PAYMENT,
    },
    "instapay": {
        "name": "InstaPay",
        "name_ar": "انستاباي",
        "colors": ["#EC008C", "#00ADEF"],
        "icon": ft.Icons.SWIPE_RIGHT_OUTLINED,
    },
    "bank": {
        "name": "Bank Account",
        "name_ar": "حساب بنكي",
        "colors": ["#005A70", "#003A48"],
        "icon": ft.Icons.ACCOUNT_BALANCE,
    },
    "unspecified": {
        "name": "Unspecified",
        "name_ar": "غير محدد",
        "colors": ["#4E6E5D", "#2E4E3D"],
        "icon": ft.Icons.HELP_OUTLINE,
    }
}

class DashboardView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase, server=None):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.server = server
        self.expand = True
        self.padding = 20

        # KPI Controls
        self.balance_text = ft.Text("0.00 EGP", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.income_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.expenses_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.count_text = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)

        # Wallets grid container
        self.wallets_row = ft.Row(wrap=True, spacing=15)

        # Recent Activity List
        self.activity_list = ft.ListView(expand=True, spacing=10)

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                        ft.Text("Dashboard / لوحة التحكم", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Re-sync / إعادة المزامنة",
                            icon=ft.Icons.SYNC_ROUNDED,
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.BLUE_800,
                            on_click=self._handle_resync,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding(15, 10, 15, 10),
                            )
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                # KPI Cards Row
                ft.Row(
                    controls=[
                        self._build_aggregate_balance_card("Total Balance / الرصيد الإجمالي", self.balance_text, ft.Icons.ACCOUNT_BALANCE_WALLET, ["#3E2723", "#1A0F0A"]),
                        self._build_kpi_card("Monthly Income / الدخل الشهري", self.income_text, ft.Icons.ARROW_DOWNWARD_ROUNDED, ft.Colors.GREEN_900, ft.Colors.GREEN_400),
                        self._build_kpi_card("Monthly Expenses / المصاريف الشهرية", self.expenses_text, ft.Icons.ARROW_UPWARD_ROUNDED, ft.Colors.RED_900, ft.Colors.RED_400),
                        self._build_kpi_card("Total TXs / إجمالي العمليات", self.count_text, ft.Icons.SYNC_ALT_ROUNDED, ft.Colors.BLUE_GREY_900, ft.Colors.BLUE_400),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True
                ),
                
                ft.Divider(height=25, color=ft.Colors.WHITE24),

                # Wallets Section
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=ft.Colors.AMBER_400, size=24),
                        ft.Text("My Wallets & Accounts / حساباتي ومحافظي", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Container(
                    content=self.wallets_row,
                    margin=ft.Margin(left=0, top=5, right=0, bottom=15)
                ),
                
                ft.Divider(height=10, color=ft.Colors.WHITE24),
                
                # Recent Activity Header
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, color=ft.Colors.BLUE_400, size=24),
                        ft.Text("Recent Activity (Live) / آخر العمليات (مباشر)", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Container(
                    content=self.activity_list,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=15,
                    bgcolor=ft.Colors.BLACK26,
                    padding=15,
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    def _build_aggregate_balance_card(self, title: str, text_control: ft.Text, icon: str, colors: list):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, color=ft.Colors.WHITE70, size=20), ft.Text(title, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500)], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    text_control
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=240,
            height=130,
            gradient=ft.LinearGradient(
                colors=colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLACK45),
            scale=1.0,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._handle_card_hover
        )

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, bg_color: str, accent_color: str):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, color=accent_color, size=20), ft.Text(title, color=ft.Colors.WHITE54)], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    text_control
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=220,
            height=130,
            bgcolor=bg_color,
            border_radius=15,
            padding=15,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, accent_color)),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK38),
            scale=1.0,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._handle_card_hover
        )

    def _handle_card_hover(self, e):
        e.control.scale = 1.03 if e.data == "true" else 1.0
        e.control.update()

    def _build_wallet_card(self, wallet_id: str, balance: float, active: bool):
        styling = WALLET_STYLING.get(wallet_id, WALLET_STYLING["unspecified"])
        name = styling["name"]
        name_ar = styling["name_ar"]
        colors = styling["colors"]
        icon = styling["icon"]

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, color=ft.Colors.WHITE70, size=24),
                            ft.Column(
                                controls=[
                                    ft.Text(name, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                    ft.Text(name_ar, size=10, color=ft.Colors.WHITE70),
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.START
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(expand=True),
                    ft.Column(
                        controls=[
                            ft.Text("Balance / الرصيد", size=10, color=ft.Colors.WHITE60),
                            ft.Text(f"{balance:,.2f} EGP", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                        ],
                        spacing=2
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=180,
            height=110,
            gradient=ft.LinearGradient(
                colors=colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=12,
            padding=12,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color=ft.Colors.BLACK26),
            scale=1.0,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._handle_card_hover
        )

    def update_data(self):
        """يُستدعى لتحديث البيانات من قاعدة البيانات"""
        kpi = self.db.get_kpi_summary()
        self.balance_text.value = f"{kpi['current_balance']:,.2f} EGP"
        self.income_text.value = f"+{kpi['income']:,.2f} EGP"
        self.expenses_text.value = f"-{kpi['expenses']:,.2f} EGP"
        self.count_text.value = str(kpi['transactions_count'])

        # تحديث قائمة المحافظ
        wallet_balances = kpi.get("wallet_balances", {})
        new_wallets = []
        
        # نعرض فقط المحافظ التي يملكها العميل (توجد في wallet_balances)
        for w_id in WALLET_STYLING.keys():
            if w_id not in wallet_balances:
                continue
            bal = wallet_balances.get(w_id, 0.0)
            new_wallets.append(
                self._build_wallet_card(w_id, bal, True)
            )
        self.wallets_row.controls = new_wallets

        # تحديث قائمة آخر العمليات
        recent_txs = self.db.get_all_transactions()[:15] # آخر 15
        new_activity = []
        
        if not recent_txs:
            new_activity.append(
                ft.Container(
                    content=ft.Text("No recent transactions / لا يوجد عمليات مؤخراً", color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER),
                    alignment=ft.alignment.Alignment.CENTER,
                    padding=20
                )
            )
        else:
            for tx in recent_txs:
                icon_color = ft.Colors.GREEN_400 if tx.type.value == "RECEIVED" else ft.Colors.RED_400 if tx.type.value in ["SENT", "PURCHASE", "BILL"] else ft.Colors.BLUE_400
                icon_name = ft.Icons.CALL_RECEIVED_ROUNDED if tx.type.value == "RECEIVED" else ft.Icons.CALL_MADE_ROUNDED
                
                w_style = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
                w_name = w_style["name"]
                w_colors = w_style["colors"]
                
                new_activity.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon_name, color=icon_color, size=24),
                                ft.Column(
                                    controls=[
                                        ft.Text(f"{tx.type.value} — {tx.amount:,.2f} EGP", weight=ft.FontWeight.BOLD, size=15),
                                        ft.Text(
                                            f"Counterpart: {tx.counterpart or 'Unknown'} | Date: {tx.sms_timestamp.strftime('%Y-%m-%d %H:%M')}" + (f" | Bal: {tx.balance_after:,.2f}" if tx.balance_after >= 0 else ""),
                                            color=ft.Colors.WHITE54,
                                            size=12
                                        ),
                                    ],
                                    expand=True,
                                    spacing=2
                                ),
                                ft.Container(
                                    content=ft.Text(w_name, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                    gradient=ft.LinearGradient(colors=w_colors),
                                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                                    border_radius=6,
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        padding=12,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        border_radius=10,
                        border=ft.Border.all(1, ft.Colors.WHITE10),
                    )
                )
        self.activity_list.controls = new_activity
        
        self.flet_page.update()

    def _handle_resync(self, e):
        if not self.server or self.server.connected_clients == 0:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text("الموبايل غير متصل. يرجى توصيل تطبيق الموبايل أولاً لإعادة المزامنة.", size=16, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.RED_700,
            )
            self.flet_page.snack_bar.open = True
            self.flet_page.update()
            return

        import asyncio
        from shared.protocol import make_force_sms_scan
        try:
            # إرسال أمر إعادة المزامنة لجميع العملاء المتصلين
            asyncio.create_task(self.server._broadcast(make_force_sms_scan()))
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text("تم إرسال طلب إعادة المزامنة وقراءة الرسائل التاريخية للموبايل بنجاح!", size=16, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN_700,
            )
            self.flet_page.snack_bar.open = True
        except Exception as ex:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text(f"حدث خطأ أثناء إرسال طلب المزامنة: {ex}", size=16, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.RED_700,
            )
            self.flet_page.snack_bar.open = True
        self.flet_page.update()
