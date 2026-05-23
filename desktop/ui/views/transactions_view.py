# desktop/ui/views/transactions_view.py
import flet as ft
from desktop.db.database import DesktopDatabase

WALLET_BADGES = {
    "vodafone_cash": {"name": "Vodafone Cash", "colors": ["#450A0A", "#0B0F19"], "accent_color": "#EF4444"},
    "orange_cash":   {"name": "Orange Cash",   "colors": ["#431407", "#0B0F19"], "accent_color": "#F97316"},
    "etisalat_cash": {"name": "Etisalat Cash", "colors": ["#14532D", "#0B0F19"], "accent_color": "#22C55E"},
    "we_pay":        {"name": "WE Pay",        "colors": ["#3B0764", "#0B0F19"], "accent_color": "#A855F7"},
    "instapay":      {"name": "InstaPay",      "colors": ["#1E1B4B", "#311042"], "accent_color": "#EC008C"},
    "bank":          {"name": "Bank Account",  "colors": ["#115E59", "#0B0F19"], "accent_color": "#06B6D4"},
    "unspecified":   {"name": "Unspecified",   "colors": ["#1E293B", "#0F172A"], "accent_color": "#64748B"},
}

PROFIT_STATUS_STYLE = {
    "UNSET":     {"icon": ft.Icons.HELP_OUTLINE_ROUNDED,       "color": ft.Colors.AMBER_400,   "tooltip": "لم يُحدَّد — اضغط للتحديد"},
    "IN_WALLET": {"icon": ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, "color": ft.Colors.GREEN_400, "tooltip": "الربح في المحفظة ✓"},
    "CASH":      {"icon": ft.Icons.MONETIZATION_ON_ROUNDED,    "color": ft.Colors.CYAN_300,    "tooltip": "الربح استُلم نقداً 💵"},
    "NONE":      {"icon": ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, "color": ft.Colors.WHITE30,  "tooltip": "لا يوجد ربح"},
}

class TransactionsView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        # Pagination state
        self.current_page = 1
        self.page_size = 50

        # Consistent Input styling helper
        input_style = {
            "border_radius": 12,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": ft.Colors.BLUE_ACCENT,
            "filled": True
        }

        self.search_field = ft.TextField(
            label="Search (Number, Text...) / البحث",
            width=220,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.apply_filters,
            **input_style
        )
        
        # Filter Controls
        self.type_dropdown = ft.Dropdown(
            label="Type / النوع",
            width=155,
            options=[
                ft.dropdown.Option("ALL", "All / الكل"),
                ft.dropdown.Option("RECEIVED", "✅ RECEIVED"),
                ft.dropdown.Option("SENT", "📤 SENT"),
                ft.dropdown.Option("ATM_WITHDRAWAL", "🏧 ATM Withdrawal"),
                ft.dropdown.Option("ATM_DEPOSIT", "🏦 ATM Deposit"),
                ft.dropdown.Option("BILL", "🧾 BILL"),
                ft.dropdown.Option("PURCHASE", "🛒 PURCHASE"),
                ft.dropdown.Option("TOPUP", "📱 TOPUP"),
            ],
            value="ALL",
            on_select=self.apply_filters,
            **input_style
        )

        self.wallet_dropdown = ft.Dropdown(
            label="Wallet / المحفظة",
            width=160,
            options=[
                ft.dropdown.Option("ALL", "All / الكل"),
                ft.dropdown.Option("vodafone_cash", "Vodafone Cash"),
                ft.dropdown.Option("orange_cash", "Orange Cash"),
                ft.dropdown.Option("etisalat_cash", "Etisalat Cash"),
                ft.dropdown.Option("we_pay", "WE Pay"),
                ft.dropdown.Option("instapay", "InstaPay"),
                ft.dropdown.Option("bank", "Bank Account"),
                ft.dropdown.Option("unspecified", "Unspecified"),
            ],
            value="ALL",
            on_select=self.apply_filters,
            **input_style
        )
        
        self.fee_filter_dropdown = ft.Dropdown(
            label="Profit Filter / أرباح",
            width=165,
            options=[
                ft.dropdown.Option("ALL",       "All / الكل"),
                ft.dropdown.Option("WITH_FEES", "With Profit / بأرباح"),
                ft.dropdown.Option("WITHOUT_FEES", "No Profit / بدون أرباح"),
            ],
            value="ALL",
            on_select=self.apply_filters,
            **input_style
        )
        self.profit_status_dropdown = ft.Dropdown(
            label="Profit Status / حالة الربح",
            width=180,
            options=[
                ft.dropdown.Option("ALL",       "All / الكل"),
                ft.dropdown.Option("UNSET",     "🟡 غير محددة"),
                ft.dropdown.Option("IN_WALLET", "💳 في المحفظة"),
                ft.dropdown.Option("CASH",      "💵 نقداً"),
                ft.dropdown.Option("NONE",      "⬜ لا ربح"),
            ],
            value="ALL",
            on_select=self.apply_filters,
            **input_style
        )
        
        self.min_amount = ft.TextField(
            label="Min Amount / الأدنى", 
            width=110, 
            keyboard_type=ft.KeyboardType.NUMBER, 
            on_submit=self.apply_filters,
            **input_style
        )
        self.max_amount = ft.TextField(
            label="Max Amount / الأقصى", 
            width=110, 
            keyboard_type=ft.KeyboardType.NUMBER, 
            on_submit=self.apply_filters,
            **input_style
        )
        
        self.start_date = ft.TextField(
            label="Start (YYYY-MM-DD)", 
            width=150, 
            on_submit=self.apply_filters,
            **input_style
        )
        self.end_date = ft.TextField(
            label="End (YYYY-MM-DD)", 
            width=150, 
            on_submit=self.apply_filters,
            **input_style
        )

        self.btn_filter = ft.ElevatedButton(
            "Filter / تصفية", 
            on_click=self.apply_filters, 
            icon=ft.Icons.FILTER_ALT,
            color=ft.Colors.WHITE,
            bgcolor="#1E3A8A",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(15, 18, 15, 18),
            )
        )
        self.btn_clear = ft.OutlinedButton(
            "Clear / مسح", 
            on_click=self.clear_filters, 
            icon=ft.Icons.CLEAR,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(15, 18, 15, 18),
            )
        )

        # DataTable
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date & Time / التاريخ والوقت", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Type / النوع",                 weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Wallet / المحفظة",             weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Amount / المبلغ",              weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Profit / الأرباح",             weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Status / الحالة",              weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)),
                ft.DataColumn(ft.Text("Balance / الرصيد",             weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Counterpart / الطرف الآخر",   weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
            ],
            rows=[],
            expand=True,
            heading_row_color="#0B0F19",
            vertical_lines=ft.BorderSide(1, ft.Colors.WHITE10),
            horizontal_lines=ft.BorderSide(1, ft.Colors.WHITE10),
        )

        # Scrollable container for the table
        self.table_container = ft.Column([self.data_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        # Pagination components
        self.prev_button = ft.IconButton(
            icon=ft.Icons.NAVIGATE_BEFORE_ROUNDED,
            on_click=self.go_prev_page,
            disabled=True,
        )
        self.next_button = ft.IconButton(
            icon=ft.Icons.NAVIGATE_NEXT_ROUNDED,
            on_click=self.go_next_page,
            disabled=True,
        )
        self.page_info = ft.Text("Page 1 of 1 (0 transactions)", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70)
        self.page_size_dropdown = ft.Dropdown(
            label="Rows / عدد الصفوف",
            width=140,
            options=[
                ft.dropdown.Option("20"),
                ft.dropdown.Option("50"),
                ft.dropdown.Option("100"),
                ft.dropdown.Option("200"),
            ],
            value="50",
            on_select=self.on_page_size_change,
            **input_style
        )
        
        self.pagination_row = ft.Row(
            controls=[
                self.prev_button,
                self.page_info,
                self.next_button,
                ft.Container(width=20),
                self.page_size_dropdown
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                        ft.Text("Transactions Archive / سجل العمليات التفصيلي", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Divider(height=10, color=ft.Colors.WHITE24),
                
                # Filters Row
                ft.Container(
                    content=ft.Column([
                        ft.Row(
                            controls=[
                                self.search_field,
                                self.type_dropdown,
                                self.wallet_dropdown,
                                self.fee_filter_dropdown,
                                self.profit_status_dropdown,
                            ],
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10
                        ),
                        ft.Row(
                            controls=[
                                self.min_amount,
                                self.max_amount,
                                self.start_date,
                                self.end_date,
                                self.btn_filter,
                                self.btn_clear
                            ],
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10
                        ),
                    ], spacing=8),
                    bgcolor="#0B0F19",
                    padding=15,
                    border_radius=15,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    margin=ft.Margin(left=0, top=0, right=0, bottom=10)
                ),
                
                # Table
                ft.Container(
                    content=self.table_container,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=15,
                    bgcolor=ft.Colors.BLACK26,
                    padding=10
                ),
                
                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                # Pagination
                self.pagination_row
            ]
        )

    def go_prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self._trigger_update()

    def go_next_page(self, e):
        self.current_page += 1
        self._trigger_update()

    def on_page_size_change(self, e):
        self.page_size = int(self.page_size_dropdown.value)
        self.current_page = 1
        self._trigger_update()

    def _trigger_update(self):
        search_val = self.search_field.value if self.search_field.value else None
        min_val = float(self.min_amount.value) if self.min_amount.value else None
        max_val = float(self.max_amount.value) if self.max_amount.value else None
        start = self.start_date.value if self.start_date.value else None
        end = self.end_date.value if self.end_date.value else None
        type_val = self.type_dropdown.value
        wallet_val = self.wallet_dropdown.value
        fee_val = self.fee_filter_dropdown.value
        profit_status_val = self.profit_status_dropdown.value

        self.update_data(
            type_filter=type_val,
            start_date=start,
            end_date=end,
            min_amount=min_val,
            max_amount=max_val,
            search_query=search_val,
            wallet_filter=wallet_val,
            fee_filter=fee_val,
            profit_status_filter=profit_status_val
        )

    def apply_filters(self, e=None):
        self.current_page = 1
        self._trigger_update()

    def clear_filters(self, e=None):
        self.search_field.value = ""
        self.type_dropdown.value = "ALL"
        self.wallet_dropdown.value = "ALL"
        self.fee_filter_dropdown.value = "ALL"
        self.profit_status_dropdown.value = "ALL"
        self.min_amount.value = ""
        self.max_amount.value = ""
        self.start_date.value = ""
        self.end_date.value = ""
        self.current_page = 1
        self.update_data()

    def update_data(self, type_filter="ALL", start_date=None, end_date=None, min_amount=None, max_amount=None, search_query=None, wallet_filter="ALL", fee_filter="ALL", profit_status_filter="ALL"):
        """تحديث بيانات الجدول مع الفلاتر"""
        try:
            total_count = self.db.get_transactions_count(
                type_filter=type_filter,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search_query=search_query,
                wallet_filter=wallet_filter,
                fee_filter=fee_filter,
                profit_status_filter=profit_status_filter
            )
            total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
            
            if self.current_page > total_pages:
                self.current_page = total_pages
                
            start_idx = (self.current_page - 1) * self.page_size
            
            paginated_txs = self.db.get_all_transactions(
                type_filter=type_filter,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search_query=search_query,
                wallet_filter=wallet_filter,
                limit=self.page_size,
                offset=start_idx,
                fee_filter=fee_filter,
                profit_status_filter=profit_status_filter
            )
        except Exception as ex:
            print(f"Error fetching filtered data: {ex}")
            total_count = 0
            total_pages = 1
            paginated_txs = []

        self.prev_button.disabled = (self.current_page == 1)
        self.next_button.disabled = (self.current_page == total_pages)
        self.page_info.value = f"Page {self.current_page} of {total_pages} ({total_count} transactions)"

        self.data_table.rows.clear()
        
        for idx, tx in enumerate(paginated_txs):
            # Color coding per transaction type
            tx_val = tx.type.value
            if tx_val == "RECEIVED":
                amount_color = ft.Colors.GREEN_400
            elif tx_val == "ATM_DEPOSIT":
                amount_color = ft.Colors.TEAL_300
            elif tx_val == "ATM_WITHDRAWAL":
                amount_color = ft.Colors.ORANGE_400
            else:
                amount_color = ft.Colors.RED_400
            
            # Wallet badge
            w_info = WALLET_BADGES.get(tx.wallet_id, WALLET_BADGES["unspecified"])
            wallet_cell = ft.DataCell(
                ft.Container(
                    content=ft.Text(w_info["name"], size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    gradient=ft.LinearGradient(colors=w_info["colors"]),
                    padding=ft.Padding(left=10, top=5, right=10, bottom=5),
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.2, w_info["accent_color"]))
                )
            )

            fee = self.db.calculate_fee(tx)
            fee_color = ft.Colors.AMBER_400 if fee > 0 else ft.Colors.WHITE38
            fee_text = f"+{fee:,.2f}" if fee > 0 else "-"

            # Profit status icon (clickable only when fee > 0)
            ps = getattr(tx, "profit_status", "UNSET") or "UNSET"
            ps_style = PROFIT_STATUS_STYLE.get(ps, PROFIT_STATUS_STYLE["UNSET"])
            if fee > 0:
                status_cell = ft.DataCell(
                    ft.IconButton(
                        icon=ps_style["icon"],
                        icon_color=ps_style["color"],
                        icon_size=20,
                        tooltip=ps_style["tooltip"],
                        on_click=lambda ev, _tx=tx, _fee=fee: self._show_profit_dialog(_tx, _fee),
                    )
                )
            else:
                status_cell = ft.DataCell(
                    ft.Icon(ft.Icons.REMOVE_OUTLINED, color=ft.Colors.WHITE24, size=16)
                )

            # Alternate row background color
            row_color = ft.Colors.with_opacity(0.04, ft.Colors.WHITE) if idx % 2 != 0 else ft.Colors.TRANSPARENT

            cp = tx.counterpart or "—"
            if cp != "—":
                tx_type_str = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
                if tx_type_str == "RECEIVED":
                    cp = f"📥 من: {cp}"
                elif tx_type_str == "SENT":
                    cp = f"📤 إلى: {cp}"
                elif tx_type_str == "TOPUP":
                    cp = f"📱 لـ: {cp}"
                elif tx_type_str == "BILL":
                    cp = f"🧾 لـ: {cp}"

            self.data_table.rows.append(
                ft.DataRow(
                    color=row_color,
                    cells=[
                        ft.DataCell(ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M'), color=ft.Colors.WHITE70)),
                        ft.DataCell(ft.Text(tx.type.value, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                        wallet_cell,
                        ft.DataCell(ft.Text(f"{tx.amount:,.2f} EGP", color=amount_color, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(fee_text, color=fee_color, weight=ft.FontWeight.BOLD if fee > 0 else ft.FontWeight.NORMAL, text_align=ft.TextAlign.RIGHT)),
                        status_cell,
                        ft.DataCell(ft.Text(f"{tx.balance_after:,.2f} EGP" if tx.balance_after >= 0 else "N/A", color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(cp, color=ft.Colors.WHITE70)),
                    ]
                )
            )
        
        self.flet_page.update()

    # ────────────────────────────────────────────────────────────────────────
    # Profit Status Dialog
    # ────────────────────────────────────────────────────────────────────────

    def _show_profit_dialog(self, tx, fee: float):
        """نافذة حوار: تحديد حالة الربح لعملية معينة"""
        ps = getattr(tx, "profit_status", "UNSET") or "UNSET"
        ps_style = PROFIT_STATUS_STYLE.get(ps, PROFIT_STATUS_STYLE["UNSET"])

        tx_type_str = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
        if tx_type_str == "RECEIVED":
            phone_label = "الرقم المحوّل منه / From"
        elif tx_type_str == "SENT":
            phone_label = "الرقم المحوّل إليه / To"
        elif tx_type_str == "TOPUP":
            phone_label = "رقم الشحن / Top-up"
        elif tx_type_str == "BILL":
            phone_label = "المستلم / Merchant"
        else:
            phone_label = "الطرف الآخر / Counterpart"

        custom_dlg = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.PERCENT_ROUNDED, color=ft.Colors.AMBER_400, size=24),
                                ft.Text("حالة الربح / Profit Status", weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE, size=16),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"💰 الربح المحتسب: {fee:,.2f} EGP",
                                        size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                                ft.Text(f"المحفظة: {tx.wallet_id or '—'} | النوع: {tx.type.value}",
                                        size=12, color=ft.Colors.WHITE54),
                                ft.Text(f"{phone_label}: {tx.counterpart or '—'}",
                                        size=12, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500),
                                ft.Divider(height=5, color=ft.Colors.WHITE10),
                                ft.Row([
                                    ft.Icon(ps_style["icon"], color=ps_style["color"], size=14),
                                    ft.Text(f"الحالة الحالية: {ps}", color=ps_style["color"], size=12),
                                ], spacing=5),
                            ], spacing=5),
                            bgcolor="#151B2E",
                            border_radius=12,
                            padding=15,
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.AMBER_400)),
                        ),
                        ft.Container(height=10),
                        ft.Text("اختر حالة الربح:", size=13, color=ft.Colors.WHITE70),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "💳 في المحفظة",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#14532D",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_profit_status(tx, fee, "IN_WALLET", custom_dlg),
                                ),
                                ft.ElevatedButton(
                                    "💵 نقداً",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#78350F",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_profit_status(tx, fee, "CASH", custom_dlg),
                                ),
                                ft.ElevatedButton(
                                    "✖ لا يوجد ربح",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#1E293B",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_profit_status(tx, fee, "NONE", custom_dlg),
                                ),
                                ft.TextButton(
                                    "إلغاء / Cancel",
                                    style=ft.ButtonStyle(color=ft.Colors.WHITE54),
                                    on_click=lambda e: self._close_dialog(custom_dlg),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            wrap=True,
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
        self.flet_page.show_dialog_overlay(custom_dlg)

    def _close_dialog(self, dlg):
        self.flet_page.close_dialog_overlay(dlg)

    def _set_profit_status(self, tx, fee: float, status: str, dlg):
        """حفظ حالة الربح وتسجيل إدخال نقدي إن كانت نقداً"""
        tx_id  = tx.transaction_id
        raw_sms = tx.raw_sms

        ok = self.db.mark_profit_status(tx_id, raw_sms, status)
        if ok and status == "CASH":
            # تسجيل الربح في سجل النقدية تلقائياً
            desc = f"ربح من {tx.type.value} — {tx.wallet_id or ''} — {tx.amount:,.2f} EGP"
            self.db.add_cash_entry("PROFIT_IN", fee, desc, source_tx_id=str(tx_id or ""))

        self._close_dialog(dlg)

        status_labels = {"IN_WALLET": "💳 في المحفظة", "CASH": "💵 نقداً", "NONE": "✖ لا ربح"}
        if ok:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text(f"✅ تم تحديد الربح كـ: {status_labels.get(status, status)}", size=14, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN_800,
            )
        else:
            self.flet_page.snack_bar = ft.SnackBar(
                content=ft.Text("❌ فشل التحديث، حاول مرة أخرى.", size=14),
                bgcolor=ft.Colors.RED_700,
            )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()
        # إعادة رسم الجدول لتحديث الأيقونة
        self.apply_filters()
