# desktop/ui/views/dashboard_view.py
import flet as ft
from datetime import datetime
import calendar
from desktop.db.database import DesktopDatabase
from shared.config import WALLET_SENDERS

WALLET_STYLING = {
    "vodafone_cash": {
        "name": "Vodafone Cash",
        "name_ar": "فودافون كاش",
        "colors": ["#450A0A", "#0B0F19"],
        "accent_color": "#EF4444",
        "icon": ft.Icons.PHONE_ANDROID,
    },
    "orange_cash": {
        "name": "Orange Cash",
        "name_ar": "أورنج كاش",
        "colors": ["#431407", "#0B0F19"],
        "accent_color": "#F97316",
        "icon": ft.Icons.MONEY_ROUNDED,
    },
    "etisalat_cash": {
        "name": "Etisalat Cash",
        "name_ar": "اتصالات كاش",
        "colors": ["#14532D", "#0B0F19"],
        "accent_color": "#22C55E",
        "icon": ft.Icons.PHONELINK_RING,
    },
    "we_pay": {
        "name": "WE Pay",
        "name_ar": "وي باي",
        "colors": ["#3B0764", "#0B0F19"],
        "accent_color": "#A855F7",
        "icon": ft.Icons.PAYMENT,
    },
    "bank": {
        "name": "Bank / InstaPay",
        "name_ar": "حساب بنكي / انستاباي",
        "colors": ["#115E59", "#0B0F19"],
        "accent_color": "#06B6D4",
        "icon": ft.Icons.ACCOUNT_BALANCE,
    },
    "unspecified": {
        "name": "Unspecified",
        "name_ar": "غير محدد",
        "colors": ["#1E293B", "#0F172A"],
        "accent_color": "#64748B",
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
        self.cash_balance_text = ft.Text("0.00 EGP", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.cash_profit_text = ft.Text("0.00 EGP", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
        self.income_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.expenses_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.count_text = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
        self.fees_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)

        # Wallets grid container
        self.wallets_row = ft.Row(wrap=True, spacing=15)

        # Recent Activity List
        self.activity_list = ft.ListView(expand=True, spacing=10)

        # Month Selector Dropdown
        # Month Selector Dropdown
        self.month_dropdown = ft.Dropdown(
            label="Period / الفترة",
            width=180,
            options=[
                ft.dropdown.Option("TODAY", "Today / اليوم"),
                ft.dropdown.Option("YESTERDAY", "Yesterday / أمس"),
                ft.dropdown.Option("THIS_WEEK", "This Week / هذا الأسبوع"),
                ft.dropdown.Option("THIS_MONTH", "This Month / هذا الشهر"),
                ft.dropdown.Option("ALL_TIME", "All Time / كل الأوقات"),
                ft.dropdown.Option("CUSTOM", "Custom Period / فترة مخصصة"),
            ],
            value="THIS_MONTH",
            on_select=self._handle_period_change,
            border_radius=12,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        # Date pickers
        self.start_date_picker = ft.DatePicker(
            on_change=self._handle_start_date_picked,
            first_date=datetime(2024, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        self.end_date_picker = ft.DatePicker(
            on_change=self._handle_end_date_picked,
            first_date=datetime(2024, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        self.flet_page.overlay.append(self.start_date_picker)
        self.flet_page.overlay.append(self.end_date_picker)

        # Custom date text fields
        self.start_date_field = ft.TextField(
            label="Start / من",
            value=datetime.now().strftime("%Y-%m-%d"),
            width=135,
            height=48,
            text_size=13,
            read_only=True,
            border_radius=10,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
                icon_size=18,
                icon_color=ft.Colors.BLUE_400,
                on_click=lambda e: self._open_start_picker()
            )
        )
        self.end_date_field = ft.TextField(
            label="End / إلى",
            value=datetime.now().strftime("%Y-%m-%d"),
            width=135,
            height=48,
            text_size=13,
            read_only=True,
            border_radius=10,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True,
            suffix=ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
                icon_size=18,
                icon_color=ft.Colors.BLUE_400,
                on_click=lambda e: self._open_end_picker()
            )
        )

        self.apply_btn = ft.ElevatedButton(
            "Apply / تطبيق",
            icon=ft.Icons.FILTER_ALT_ROUNDED,
            color=ft.Colors.WHITE,
            bgcolor="#1E8F8B",
            on_click=self._handle_apply_custom_period,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(12, 10, 12, 10),
            )
        )

        self.custom_date_row = ft.Row(
            controls=[
                self.start_date_field,
                self.end_date_field,
                self.apply_btn
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START,
            visible=False
        )

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                        ft.Text("Dashboard / لوحة التحكم", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Container(expand=True),
                        self.custom_date_row,
                        self.month_dropdown,
                        ft.Container(width=10),
                        ft.ElevatedButton(
                            "Re-sync / إعادة المزامنة",
                            icon=ft.Icons.SYNC_ROUNDED,
                            color=ft.Colors.WHITE,
                            bgcolor="#0F3C6D",
                            on_click=self._handle_resync,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.Padding(20, 15, 20, 15),
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
                        self._build_kpi_card("Total Balance / الرصيد الإجمالي", self.balance_text, ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, ["#1E293B", "#0F172A"], ft.Colors.AMBER_500, width=230),
                        self._build_cash_kpi_card("Cash Balance / الرصيد النقدي", self.cash_balance_text, self.cash_profit_text, ft.Icons.MONETIZATION_ON_ROUNDED, ["#1E293B", "#0F172A"], ft.Colors.TEAL_400, width=230),
                        self._build_kpi_card("Period Income / دخل الفترة", self.income_text, ft.Icons.ARROW_DOWNWARD_ROUNDED, ["#064E3B", "#022C22"], ft.Colors.GREEN_400),
                        self._build_kpi_card("Period Expenses / مصاريف الفترة", self.expenses_text, ft.Icons.ARROW_UPWARD_ROUNDED, ["#7F1D1D", "#450A0A"], ft.Colors.RED_400),
                        self._build_kpi_card("Period Profit / أرباح الفترة", self.fees_text, ft.Icons.PERCENT, ["#78350F", "#451A03"], ft.Colors.AMBER_400),
                        self._build_kpi_card("Total TXs / إجمالي العمليات", self.count_text, ft.Icons.SYNC_ALT_ROUNDED, ["#0F3C6D", "#0A2545"], ft.Colors.BLUE_400),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    wrap=True,
                    spacing=15
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
                    height=380,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=15,
                    bgcolor=ft.Colors.BLACK26,
                    padding=15,
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, gradient_colors: list, accent_color: str, width: int = 220):
        title_parts = title.split(" / ")
        title_en = title_parts[0] if len(title_parts) > 0 else title
        title_ar = title_parts[1] if len(title_parts) > 1 else ""

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, color=accent_color, size=20),
                                bgcolor=ft.Colors.with_opacity(0.12, accent_color),
                                padding=8,
                                border_radius=20,
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, accent_color)),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(title_en, color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(title_ar, color=ft.Colors.WHITE60, size=10, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                expand=True
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    ft.Container(
                        content=text_control,
                        alignment=ft.alignment.Alignment.CENTER,
                        expand=True
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=width,
            height=130,
            gradient=ft.LinearGradient(
                colors=gradient_colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=12,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.18, accent_color)),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)),
            scale=1.0,
            animate_scale=ft.Animation(250, ft.AnimationCurve.EASE_OUT_BACK),
            on_hover=self._handle_card_hover
        )

    def _build_cash_kpi_card(self, title: str, cash_text: ft.Text, profit_text: ft.Text, icon: str, gradient_colors: list, accent_color: str, width: int = 230):
        title_parts = title.split(" / ")
        title_en = title_parts[0] if len(title_parts) > 0 else title
        title_ar = title_parts[1] if len(title_parts) > 1 else ""

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, color=accent_color, size=20),
                                bgcolor=ft.Colors.with_opacity(0.12, accent_color),
                                padding=8,
                                border_radius=20,
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, accent_color)),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(title_en, color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(title_ar, color=ft.Colors.WHITE60, size=10, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                expand=True
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Actual / الفعلي", size=9, color=ft.Colors.WHITE60, weight=ft.FontWeight.W_500),
                                    cash_text
                                ],
                                spacing=1,
                                expand=True
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Profit / أرباح الدرج", size=9, color=ft.Colors.AMBER_400, weight=ft.FontWeight.W_500),
                                    profit_text
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.END
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=width,
            height=130,
            gradient=ft.LinearGradient(
                colors=gradient_colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=12,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.18, accent_color)),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)),
            scale=1.0,
            animate_scale=ft.Animation(250, ft.AnimationCurve.EASE_OUT_BACK),
            on_hover=self._handle_card_hover
        )

    def _handle_card_hover(self, e):
        e.control.scale = 1.04 if e.data == "true" else 1.0
        # If hovered, brighten the border color
        accent_color = e.control.border.top.color
        if e.data == "true":
            e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=16, color=ft.Colors.with_opacity(0.15, accent_color))
        else:
            e.control.shadow = ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK))
        e.control.update()

    def _build_wallet_card(self, wallet_id: str, balance: float, profit: float, active: bool):
        styling = WALLET_STYLING.get(wallet_id, WALLET_STYLING["unspecified"])
        name = styling["name"]
        name_ar = styling["name_ar"]
        colors = styling["colors"]
        accent_color = styling["accent_color"]
        icon = styling["icon"]

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, color=accent_color, size=22),
                                bgcolor=ft.Colors.with_opacity(0.12, accent_color),
                                padding=8,
                                border_radius=20,
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, accent_color)),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(name, size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(name_ar, size=10, color=ft.Colors.WHITE60, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                expand=True
                            ),
                            # Credit Card Chip representation
                            ft.Container(
                                width=24,
                                height=18,
                                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                                border_radius=4,
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                                opacity=0.6,
                                alignment=ft.alignment.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.SIM_CARD_OUTLINED, size=12, color=ft.Colors.WHITE54)
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ft.Container(expand=True),
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Actual Balance / الرصيد الفعلي", size=9, color=ft.Colors.WHITE60, weight=ft.FontWeight.W_500),
                                    ft.Text(f"{balance:,.2f} EGP", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                                ],
                                spacing=1,
                                expand=True
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Profit / الربح المحقق", size=9, color=ft.Colors.AMBER_400, weight=ft.FontWeight.W_500),
                                    ft.Text(f"{profit:,.2f} EGP", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
                                ],
                                spacing=1,
                                horizontal_alignment=ft.CrossAxisAlignment.END
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=220,
            height=140,
            gradient=ft.LinearGradient(
                colors=colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=12,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.22, accent_color)),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
            scale=1.0,
            animate_scale=ft.Animation(250, ft.AnimationCurve.EASE_OUT_BACK),
            on_hover=self._handle_card_hover
        )

    def _open_start_picker(self):
        self.start_date_picker.open = True
        self.flet_page.update()

    def _open_end_picker(self):
        self.end_date_picker.open = True
        self.flet_page.update()

    def _handle_start_date_picked(self, e):
        if self.start_date_picker.value:
            self.start_date_field.value = self.start_date_picker.value.strftime("%Y-%m-%d")
            self.start_date_field.update()

    def _handle_end_date_picked(self, e):
        if self.end_date_picker.value:
            self.end_date_field.value = self.end_date_picker.value.strftime("%Y-%m-%d")
            self.end_date_field.update()

    def _handle_period_change(self, e):
        if self.month_dropdown.value == "CUSTOM":
            self.custom_date_row.visible = True
        else:
            self.custom_date_row.visible = False
        self.custom_date_row.update()
        self.update_data()

    def _handle_apply_custom_period(self, e):
        self.update_data()

    def update_data(self):
        """يُستدعى لتحديث البيانات من قاعدة البيانات"""
        from datetime import datetime, timedelta
        
        selected_period = self.month_dropdown.value or "THIS_MONTH"
        
        start_date = None
        end_date = None
        db_month = None
        
        today = datetime.now()
        
        if selected_period == "TODAY":
            start_date = today.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif selected_period == "YESTERDAY":
            yesterday = today - timedelta(days=1)
            start_date = yesterday.strftime("%Y-%m-%d")
            end_date = yesterday.strftime("%Y-%m-%d")
        elif selected_period == "THIS_WEEK":
            days_since_saturday = (today.weekday() + 2) % 7
            saturday = today - timedelta(days=days_since_saturday)
            start_date = saturday.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif selected_period == "THIS_MONTH":
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif selected_period == "ALL_TIME":
            db_month = "ALL"
        elif selected_period == "CUSTOM":
            start_date = self.start_date_field.value
            end_date = self.end_date_field.value
        else:
            db_month = selected_period

        # Fetch KPIs
        kpi = self.db.get_kpi_summary(month=db_month, start_date=start_date, end_date=end_date)
        
        self.balance_text.value = f"{kpi['current_balance']:,.2f} EGP"
        
        cash_summary = self.db.get_cash_summary()
        self.cash_balance_text.value = f"{cash_summary['balance']:,.2f} EGP"
        self.cash_balance_text.color = ft.Colors.WHITE if cash_summary['balance'] >= 0 else ft.Colors.RED_400
        self.cash_profit_text.value = f"{kpi.get('profit_cash', 0.0):,.2f} EGP"

        self.income_text.value = f"+{kpi['income']:,.2f} EGP"
        self.expenses_text.value = f"-{kpi['expenses']:,.2f} EGP"
        self.count_text.value = str(kpi['transactions_count'])
        self.fees_text.value = f"{kpi.get('fees', 0.0):,.2f} EGP"

        # تحديث قائمة المحافظ
        wallet_balances = kpi.get("wallet_balances", {})
        wallet_fees = kpi.get("wallet_fees", {})
        new_wallets = []
        
        for w_id in WALLET_STYLING.keys():
            if w_id not in wallet_balances:
                continue
            bal = wallet_balances.get(w_id, 0.0)
            profit = wallet_fees.get(w_id, 0.0)
            new_wallets.append(
                self._build_wallet_card(w_id, bal, profit, True)
            )
        self.wallets_row.controls = new_wallets

        # تحديث قائمة آخر العمليات
        try:
            recent_txs = self.db.get_all_transactions(
                start_date=start_date,
                end_date=end_date,
                limit=15
            )
        except Exception as e:
            print(f"Error querying transactions for dashboard: {e}")
            recent_txs = self.db.get_all_transactions(limit=15)

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
                tx_val = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
                is_received = tx_val in ["RECEIVED", "ATM_DEPOSIT"]
                
                if tx_val == "RECEIVED":
                    icon_color = ft.Colors.GREEN_400
                    icon_name = ft.Icons.CALL_RECEIVED_ROUNDED
                    row_bg = "#0A1D15"
                elif tx_val == "ATM_DEPOSIT":
                    icon_color = ft.Colors.TEAL_400
                    icon_name = ft.Icons.ACCOUNT_BALANCE_ROUNDED
                    row_bg = "#0A1D1D"
                elif tx_val == "ATM_WITHDRAWAL":
                    icon_color = ft.Colors.ORANGE_400
                    icon_name = ft.Icons.ATM_ROUNDED
                    row_bg = "#1A1008"
                elif tx_val in ["SENT", "PURCHASE", "BILL", "TOPUP"]:
                    icon_color = ft.Colors.RED_400
                    icon_name = ft.Icons.CALL_MADE_ROUNDED
                    row_bg = "#0D131F"
                else:
                    icon_color = ft.Colors.BLUE_400
                    icon_name = ft.Icons.SWAP_HORIZ_ROUNDED
                    row_bg = "#0D131F"
                
                w_style = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
                w_name = w_style["name"]
                w_colors = w_style["colors"]
                
                fee = self.db.calculate_fee(tx)
                fee_badge = None
                if fee > 0:
                    fee_badge = ft.Container(
                        content=ft.Text(f"+{fee:.2f} Profit / ربح", size=9, color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.AMBER_400),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.AMBER_400)),
                        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                        border_radius=12
                    )

                cp = tx.counterpart or "Unknown"
                if tx_val == "RECEIVED":
                    cp_label = f"المرسل / From: {cp}"
                elif tx_val == "SENT":
                    cp_label = f"المستلم / To: {cp}"
                elif tx_val == "TOPUP":
                    cp_label = f"رقم الشحن / Top-up To: {cp}"
                elif tx_val == "BILL":
                    cp_label = f"الجهة / Merchant: {cp}"
                else:
                    cp_label = f"الطرف الآخر / Counterpart: {cp}"
                
                date_str = ""
                if tx.sms_timestamp:
                    try:
                        date_str = tx.sms_timestamp.strftime("%Y-%m-%d %I:%M %p")
                    except Exception:
                        date_str = str(tx.sms_timestamp)

                new_activity.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            content=ft.Icon(icon_name, color=icon_color, size=18),
                                            bgcolor=ft.Colors.with_opacity(0.1, icon_color),
                                            padding=8,
                                            border_radius=10,
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text(f"{tx.amount:,.2f} EGP", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                ft.Text(cp_label, size=11, color=ft.Colors.WHITE54),
                                            ],
                                            spacing=2,
                                            horizontal_alignment=ft.CrossAxisAlignment.START,
                                        )
                                    ],
                                    spacing=10,
                                    expand=True
                                ),
                                ft.Row(
                                    controls=[
                                        fee_badge if fee_badge else ft.Container(),
                                        ft.Container(
                                            content=ft.Text(w_name, size=10, color=w_style["accent_color"], weight=ft.FontWeight.W_500),
                                            bgcolor=w_colors[0],
                                            padding=ft.Padding(10, 4, 10, 4),
                                            border_radius=8,
                                        ),
                                        ft.Text(date_str, size=11, color=ft.Colors.WHITE38),
                                    ],
                                    spacing=15,
                                    alignment=ft.MainAxisAlignment.END
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        bgcolor=row_bg,
                        padding=ft.Padding(15, 10, 15, 10),
                        border_radius=12,
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
            # إرسال أمر إعادة المزامنة لجميع العملاء المتصلين بشكل آمن عبر الخيوط
            self.server.broadcast_threadsafe(make_force_sms_scan())
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
