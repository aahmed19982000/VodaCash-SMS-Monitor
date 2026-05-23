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
    "instapay": {
        "name": "InstaPay",
        "name_ar": "انستاباي",
        "colors": ["#1E1B4B", "#311042"],
        "accent_color": "#EC008C",
        "icon": ft.Icons.SWIPE_RIGHT_OUTLINED,
    },
    "bank": {
        "name": "Bank Account",
        "name_ar": "حساب بنكي",
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
        self.cash_balance_text = ft.Text("0.00 EGP", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.income_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.expenses_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.count_text = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
        self.fees_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)

        # Wallets grid container
        self.wallets_row = ft.Row(wrap=True, spacing=15)

        # Recent Activity List
        self.activity_list = ft.ListView(expand=True, spacing=10)

        # Month Selector Dropdown
        self.month_dropdown = ft.Dropdown(
            label="Period / الفترة",
            width=180,
            on_select=self._handle_month_change,
            border_radius=12,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                        ft.Text("Dashboard / لوحة التحكم", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Container(expand=True),
                        self.month_dropdown,
                        ft.Container(width=10),
                        ft.ElevatedButton(
                            "Re-sync / إعادة المزامنة",
                            icon=ft.Icons.SYNC_ROUNDED,
                            color=ft.Colors.WHITE,
                            bgcolor="#1E3A8A",
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
                        self._build_kpi_card("Cash Balance / الرصيد النقدي", self.cash_balance_text, ft.Icons.MONETIZATION_ON_ROUNDED, ["#1E293B", "#0F172A"], ft.Colors.TEAL_400, width=230),
                        self._build_kpi_card("Period Income / دخل الفترة", self.income_text, ft.Icons.ARROW_DOWNWARD_ROUNDED, ["#064E3B", "#022C22"], ft.Colors.GREEN_400),
                        self._build_kpi_card("Period Expenses / مصاريف الفترة", self.expenses_text, ft.Icons.ARROW_UPWARD_ROUNDED, ["#7F1D1D", "#450A0A"], ft.Colors.RED_400),
                        self._build_kpi_card("Period Profit / أرباح الفترة", self.fees_text, ft.Icons.PERCENT, ["#78350F", "#451A03"], ft.Colors.AMBER_400),
                        self._build_kpi_card("Total TXs / إجمالي العمليات", self.count_text, ft.Icons.SYNC_ALT_ROUNDED, ["#1E3A8A", "#0F172A"], ft.Colors.BLUE_400),
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

    def _handle_card_hover(self, e):
        e.control.scale = 1.04 if e.data == "true" else 1.0
        # If hovered, brighten the border color
        accent_color = e.control.border.top.color
        if e.data == "true":
            e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=16, color=ft.Colors.with_opacity(0.15, accent_color))
        else:
            e.control.shadow = ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK))
        e.control.update()

    def _build_wallet_card(self, wallet_id: str, balance: float, active: bool):
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
                    ft.Column(
                        controls=[
                            ft.Text("Balance / الرصيد", size=9, color=ft.Colors.WHITE60, weight=ft.FontWeight.W_500),
                            ft.Text(f"{balance:,.2f} EGP", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                        ],
                        spacing=1
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=200,
            height=125,
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

    def _handle_month_change(self, e):
        self.update_data()

    def update_data(self):
        """يُستدعى لتحديث البيانات من قاعدة البيانات"""
        # 1. Update month dropdown options dynamically
        try:
            available_months = self.db.get_available_months()
        except Exception as e:
            available_months = []
            print(f"Error fetching months: {e}")

        current_month = datetime.now().strftime("%Y-%m")
        months_list = list(available_months)
        if current_month not in months_list:
            months_list.insert(0, current_month)

        expected_keys = ["ALL"] + months_list
        current_options_keys = [opt.key for opt in self.month_dropdown.options] if self.month_dropdown.options else []

        if current_options_keys != expected_keys:
            options = [ft.dropdown.Option("ALL", "All Time / كل الأوقات")]
            for m in months_list:
                options.append(ft.dropdown.Option(m, m))
            self.month_dropdown.options = options
            
            # Default to current month if not set or invalid
            if not self.month_dropdown.value or self.month_dropdown.value not in expected_keys:
                self.month_dropdown.value = current_month

        selected_period = self.month_dropdown.value
        db_month = selected_period

        kpi = self.db.get_kpi_summary(month=db_month)
        self.balance_text.value = f"{kpi['current_balance']:,.2f} EGP"
        
        cash_summary = self.db.get_cash_summary()
        self.cash_balance_text.value = f"{cash_summary['balance']:,.2f} EGP"
        self.cash_balance_text.color = ft.Colors.WHITE if cash_summary['balance'] >= 0 else ft.Colors.RED_400

        self.income_text.value = f"+{kpi['income']:,.2f} EGP"
        self.expenses_text.value = f"-{kpi['expenses']:,.2f} EGP"
        self.count_text.value = str(kpi['transactions_count'])
        self.fees_text.value = f"{kpi.get('fees', 0.0):,.2f} EGP"

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
        if selected_period == "ALL":
            recent_txs = self.db.get_all_transactions(limit=15)
        else:
            try:
                year, month = map(int, selected_period.split('-'))
                last_day = calendar.monthrange(year, month)[1]
                start_date = f"{selected_period}-01"
                end_date = f"{selected_period}-{last_day}"
                recent_txs = self.db.get_all_transactions(start_date=start_date, end_date=end_date, limit=15)
            except Exception as e:
                print(f"Error parsing period for transactions query: {e}")
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
                tx_val = tx.type.value
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
                elif tx_val in ["SENT", "PURCHASE", "BILL"]:
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
                    cp_label = f"رقم الشحن / Top-up: {cp}"
                elif tx_val == "BILL":
                    cp_label = f"المستلم / Merchant: {cp}"
                else:
                    cp_label = f"الطرف الآخر / Counterpart: {cp}"

                new_activity.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(icon_name, color=icon_color, size=18),
                                    bgcolor=ft.Colors.with_opacity(0.08, icon_color),
                                    padding=8,
                                    border_radius=20,
                                    border=ft.Border.all(1, ft.Colors.with_opacity(0.15, icon_color)),
                                    margin=ft.Margin(left=0, top=0, right=5, bottom=0)
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Text(f"{tx.type.value} — {tx.amount:,.2f} EGP", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.WHITE),
                                                fee_badge
                                            ] if fee_badge else [ft.Text(f"{tx.type.value} — {tx.amount:,.2f} EGP", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.WHITE)],
                                            spacing=10,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                                        ),
                                        ft.Text(
                                            f"{cp_label} | Date: {tx.sms_timestamp.strftime('%Y-%m-%d %H:%M')}" + (f" | Bal: {tx.balance_after:,.2f} EGP" if tx.balance_after >= 0 else ""),
                                            color=ft.Colors.WHITE54,
                                            size=11
                                        ),
                                    ],
                                    expand=True,
                                    spacing=2
                                ),
                                ft.Container(
                                    content=ft.Text(w_name, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                    gradient=ft.LinearGradient(colors=w_colors),
                                    padding=ft.Padding(left=10, top=5, right=10, bottom=5),
                                    border_radius=12,
                                    border=ft.Border.all(1, ft.Colors.with_opacity(0.2, w_style["accent_color"]))
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        padding=12,
                        bgcolor=row_bg,
                        border_radius=12,
                        border=ft.Border(
                            left=ft.BorderSide(4, icon_color),
                            top=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
                            right=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
                            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))
                        ),
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
