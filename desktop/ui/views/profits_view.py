# desktop/ui/views/profits_view.py
import flet as ft
from datetime import datetime, timedelta
from desktop.db.database import DesktopDatabase
from shared.models import Transaction

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

PROFIT_STATUS_STYLE = {
    "UNSET":     {"label": "غير محدد", "icon": ft.Icons.HELP_OUTLINE_ROUNDED, "color": ft.Colors.AMBER_400, "bg": "#251F10"},
    "IN_WALLET": {"label": "في المحفظة", "icon": ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, "color": ft.Colors.GREEN_400, "bg": "#0A241A"},
    "CASH":      {"label": "في الدرج", "icon": ft.Icons.MONETIZATION_ON_ROUNDED, "color": ft.Colors.CYAN_300, "bg": "#0B2535"},
    "NONE":      {"label": "لا ربح", "icon": ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, "color": ft.Colors.WHITE30, "bg": "#1E293B"},
}

class ProfitsView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase, server=None):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.server = server
        self.expand = True
        self.padding = 20

        # KPI controls
        self.total_profits_text = ft.Text("0.00 EGP", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.wallet_profits_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.drawer_profits_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300)
        self.unset_profits_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)

        # Wallets row
        self.wallets_row = ft.Row(wrap=True, spacing=15)

        # Filter controls
        self.search_field = ft.TextField(
            label="Search / البحث",
            width=200,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self._handle_filter_change,
            border_radius=10,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.status_dropdown = ft.Dropdown(
            label="Profit Status / حالة الربح",
            width=180,
            options=[
                ft.dropdown.Option("ALL", "All / الكل"),
                ft.dropdown.Option("UNSET", "Pending / غير محددة"),
                ft.dropdown.Option("IN_WALLET", "In Wallet / في المحفظة"),
                ft.dropdown.Option("CASH", "Received / في الدرج"),
                ft.dropdown.Option("NONE", "No Profit / لا ربح"),
            ],
            value="ALL",
            on_select=self._handle_filter_change,
            border_radius=10,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.period_dropdown = ft.Dropdown(
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
            border_radius=10,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        # Custom dates
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

        # Transactions List
        self.transactions_list = ft.ListView(expand=True, spacing=10)

        self.setup_ui()

    def setup_ui(self):
        header = ft.Row(
            controls=[
                ft.Icon(ft.Icons.MONETIZATION_ON_ROUNDED, color=ft.Colors.AMBER_400, size=32),
                ft.Column(
                    controls=[
                        ft.Text("تفاصيل الأرباح / Profits Dashboard", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("تتبع أرباح المحافظ الإلكترونية، أرباح الخزينة، ومصادر الدخل من العمليات", size=13, color=ft.Colors.WHITE54),
                    ],
                    spacing=2
                )
            ],
            spacing=15
        )

        # KPI row
        kpi_row = ft.Row(
            controls=[
                self._build_kpi_card("Total Profits / إجمالي الأرباح", self.total_profits_text, ft.Icons.PERCENT, ["#1E293B", "#0F172A"], ft.Colors.AMBER_500, width=230),
                self._build_kpi_card("In Wallet / في المحفظة", self.wallet_profits_text, ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, ["#064E3B", "#022C22"], ft.Colors.GREEN_400),
                self._build_kpi_card("Drawer Profits / في الدرج", self.drawer_profits_text, ft.Icons.MONETIZATION_ON_ROUNDED, ["#0B2535", "#081A26"], ft.Colors.CYAN_300),
                self._build_kpi_card("Pending / معلقة", self.unset_profits_text, ft.Icons.HELP_OUTLINE_ROUNDED, ["#78350F", "#451A03"], ft.Colors.AMBER_400),
            ],
            alignment=ft.MainAxisAlignment.START,
            wrap=True,
            spacing=15
        )

        filters_row = ft.Row(
            controls=[
                self.search_field,
                self.status_dropdown,
                self.period_dropdown,
                self.custom_date_row,
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
            wrap=True
        )

        # Main Layout
        self.content = ft.Column(
            controls=[
                header,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                kpi_row,
                ft.Divider(height=15, color=ft.Colors.WHITE24),
                ft.Text("الأرباح حسب المحفظة / Profits per Wallet", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                self.wallets_row,
                ft.Divider(height=15, color=ft.Colors.WHITE24),
                ft.Text("تفاصيل العمليات المدرة للربح / Profit Transactions", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                filters_row,
                ft.Container(
                    content=self.transactions_list,
                    expand=True,
                    padding=5
                )
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

    def _build_kpi_card(self, title: str, text_ctrl: ft.Text, icon: str, gradient_colors: list, accent_color: str, width: int = 210):
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
                    text_ctrl
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=width,
            height=125,
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
        e.control.update()

    def _build_wallet_profit_card(self, wallet_id: str, profit: float):
        styling = WALLET_STYLING.get(wallet_id, WALLET_STYLING["unspecified"])
        w_name = styling["name"]
        w_name_ar = styling["name_ar"]
        colors = styling["colors"]
        accent_color = styling["accent_color"]
        icon = styling["icon"]

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, color=accent_color, size=24),
                            ft.Column(
                                controls=[
                                    ft.Text(w_name, size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                    ft.Text(w_name_ar, size=11, color=ft.Colors.WHITE54),
                                ],
                                spacing=1
                            )
                        ],
                        spacing=10
                    ),
                    ft.Container(expand=True),
                    ft.Column(
                        controls=[
                            ft.Text("Profit / أرباح المحفظة", size=9, color=ft.Colors.AMBER_400, weight=ft.FontWeight.W_500),
                            ft.Text(f"{profit:,.2f} EGP", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                        ],
                        spacing=1
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            width=210,
            height=125,
            gradient=ft.LinearGradient(
                colors=colors,
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=15,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, accent_color)),
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
        if self.period_dropdown.value == "CUSTOM":
            self.custom_date_row.visible = True
        else:
            self.custom_date_row.visible = False
        self.custom_date_row.update()
        self.update_data()

    def _handle_apply_custom_period(self, e):
        self.update_data()

    def _handle_filter_change(self, e):
        self.update_data()

    def update_data(self):
        """يُستدعى لتحديث البيانات من قاعدة البيانات"""
        selected_period = self.period_dropdown.value or "THIS_MONTH"
        
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

        # Fetch KPIs
        kpi = self.db.get_kpi_summary(month=db_month, start_date=start_date, end_date=end_date)
        
        self.total_profits_text.value = f"{kpi.get('fees', 0.0):,.2f} EGP"
        self.wallet_profits_text.value = f"{kpi.get('profit_in_wallet', 0.0):,.2f} EGP"
        self.drawer_profits_text.value = f"{kpi.get('profit_cash', 0.0):,.2f} EGP"
        self.unset_profits_text.value = f"{kpi.get('profit_unset', 0.0):,.2f} EGP"

        # Update Wallets Breakdown
        wallet_balances = kpi.get("wallet_balances", {})
        wallet_fees = kpi.get("wallet_fees", {})
        new_wallets = []
        
        for w_id in WALLET_STYLING.keys():
            if w_id == "unspecified" or w_id not in wallet_balances:
                continue
            profit = wallet_fees.get(w_id, 0.0)
            new_wallets.append(
                self._build_wallet_profit_card(w_id, profit)
            )
        self.wallets_row.controls = new_wallets

        # Update Transactions List
        search_q = self.search_field.value.strip() if self.search_field.value else None
        status_filter = self.status_dropdown.value or "ALL"

        try:
            txs = self.db.get_all_transactions(
                start_date=start_date,
                end_date=end_date,
                search_query=search_q,
                fee_filter="WITH_FEES",
                profit_status_filter=status_filter,
                limit=100
            )
        except Exception as e:
            print(f"Error querying transactions for profits page: {e}")
            txs = []

        new_activity = []

        if not txs:
            new_activity.append(
                ft.Container(
                    content=ft.Text("لا يوجد معاملات مطابقة للفلاتر أو مدرة للربح / No profit transactions found", color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER),
                    alignment=ft.alignment.Alignment.CENTER,
                    padding=30
                )
            )
        else:
            for tx in txs:
                fee = self.db.calculate_fee(tx)
                w_style = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
                w_name = w_style["name_ar"]
                w_accent = w_style["accent_color"]
                
                tx_val = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
                
                # Check status and styles
                p_status = tx.profit_status if hasattr(tx, "profit_status") else "UNSET"
                status_info = PROFIT_STATUS_STYLE.get(p_status, PROFIT_STATUS_STYLE["UNSET"])

                date_str = ""
                if tx.sms_timestamp:
                    try:
                        date_str = tx.sms_timestamp.strftime("%Y-%m-%d %I:%M %p")
                    except Exception:
                        date_str = str(tx.sms_timestamp)

                # Quick action status toggle helper
                def make_status_setter(transaction, status_val):
                    return lambda e: self._set_profit_status_on_row(transaction, status_val)

                row_card = ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    # Amount & Profit info
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=ft.Icon(ft.Icons.MONETIZATION_ON_ROUNDED, color=ft.Colors.AMBER_400, size=18),
                                                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER_400),
                                                padding=8,
                                                border_radius=10,
                                            ),
                                            ft.Column(
                                                controls=[
                                                    ft.Text(f"+{fee:,.2f} EGP (ربح)", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                                                    ft.Text(f"قيمة العملية: {tx.amount:,.2f} EGP — {tx_val}", size=11, color=ft.Colors.WHITE54),
                                                ],
                                                spacing=2
                                            )
                                        ],
                                        spacing=10,
                                        expand=True
                                    ),
                                    # Wallet and Date
                                    ft.Row(
                                        controls=[
                                            ft.Container(
                                                content=ft.Text(w_name, size=10, color=w_accent, weight=ft.FontWeight.BOLD),
                                                bgcolor=w_style["colors"][0],
                                                padding=ft.Padding(10, 4, 10, 4),
                                                border_radius=8,
                                            ),
                                            ft.Text(date_str, size=11, color=ft.Colors.WHITE38),
                                        ],
                                        spacing=15
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Divider(height=1, color=ft.Colors.WHITE10),
                            # Action Row
                            ft.Row(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(status_info["icon"], color=status_info["color"], size=16),
                                            ft.Text(f"حالة الأرباح: {status_info['label']}", size=11, color=status_info["color"], weight=ft.FontWeight.W_500),
                                        ],
                                        spacing=6,
                                        expand=True
                                    ),
                                    # Status setters
                                    ft.Row(
                                        controls=[
                                            ft.TextButton(
                                                "💳 في المحفظة",
                                                style=ft.ButtonStyle(color=ft.Colors.GREEN_400, text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600)),
                                                on_click=make_status_setter(tx, "IN_WALLET")
                                            ),
                                            ft.TextButton(
                                                "💵 في الدرج",
                                                style=ft.ButtonStyle(color=ft.Colors.CYAN_300, text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600)),
                                                on_click=make_status_setter(tx, "CASH")
                                            ),
                                            ft.TextButton(
                                                "✖ لا ربح",
                                                style=ft.ButtonStyle(color=ft.Colors.WHITE30, text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_600)),
                                                on_click=make_status_setter(tx, "NONE")
                                            ),
                                        ],
                                        spacing=5
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            )
                        ],
                        spacing=8
                    ),
                    bgcolor="#0D131F",
                    padding=ft.Padding(15, 12, 15, 12),
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.WHITE10)
                )
                new_activity.append(row_card)

        self.transactions_list.controls = new_activity
        self.flet_page.update()

    def _set_profit_status_on_row(self, tx, status_val):
        try:
            ok = self.db.mark_profit_status(tx.transaction_id, tx.raw_sms, status_val)
            if ok:
                # Refresh views thread-safely or locally
                self.update_data()
                # Update main app stats if ui_app exists
                if hasattr(self.flet_page, "ui_app") and self.flet_page.ui_app:
                    self.flet_page.ui_app.refresh_all_views()
                
                status_labels = {"IN_WALLET": "💳 أرباح في المحفظة", "CASH": "💵 أرباح في الدرج", "NONE": "✖ لا ربح"}
                self.show_snack(f"✅ تم تعديل حالة الأرباح بنجاح إلى: {status_labels.get(status_val, status_val)}", False)
            else:
                self.show_snack("❌ فشل تعديل حالة الأرباح", True)
        except Exception as e:
            print(f"Error changing status: {e}")
            self.show_snack(f"❌ خطأ: {e}", True)

    def show_snack(self, message: str, is_error: bool):
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(message, size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_800,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()
