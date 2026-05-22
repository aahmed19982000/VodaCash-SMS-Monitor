# desktop/ui/views/transactions_view.py
import flet as ft
from desktop.db.database import DesktopDatabase

WALLET_BADGES = {
    "vodafone_cash": {"name": "Vodafone Cash", "colors": ["#450A0A", "#0B0F19"], "accent_color": "#EF4444"},
    "orange_cash": {"name": "Orange Cash", "colors": ["#431407", "#0B0F19"], "accent_color": "#F97316"},
    "etisalat_cash": {"name": "Etisalat Cash", "colors": ["#14532D", "#0B0F19"], "accent_color": "#22C55E"},
    "we_pay": {"name": "WE Pay", "colors": ["#3B0764", "#0B0F19"], "accent_color": "#A855F7"},
    "instapay": {"name": "InstaPay", "colors": ["#1E1B4B", "#311042"], "accent_color": "#EC008C"},
    "bank": {"name": "Bank Account", "colors": ["#115E59", "#0B0F19"], "accent_color": "#06B6D4"},
    "unspecified": {"name": "Unspecified", "colors": ["#1E293B", "#0F172A"], "accent_color": "#64748B"},
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
            width=160,
            options=[
                ft.dropdown.Option("ALL", "All / الكل"),
                ft.dropdown.Option("WITH_FEES", "With Profit / بأرباح"),
                ft.dropdown.Option("WITHOUT_FEES", "Without Profit / بدون أرباح"),
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
                ft.DataColumn(ft.Text("Type / النوع", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Wallet / المحفظة", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Amount / المبلغ", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Profit / الأرباح", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Balance / الرصيد", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("Counterpart / الطرف الآخر", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
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
                
                # Filters Row (wrapped inside a cosmic panel)
                ft.Container(
                    content=ft.Row(
                        controls=[
                            self.search_field,
                            self.type_dropdown,
                            self.wallet_dropdown,
                            self.fee_filter_dropdown,
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

        self.update_data(
            type_filter=type_val,
            start_date=start,
            end_date=end,
            min_amount=min_val,
            max_amount=max_val,
            search_query=search_val,
            wallet_filter=wallet_val,
            fee_filter=fee_val
        )

    def apply_filters(self, e=None):
        self.current_page = 1
        self._trigger_update()

    def clear_filters(self, e=None):
        self.search_field.value = ""
        self.type_dropdown.value = "ALL"
        self.wallet_dropdown.value = "ALL"
        self.fee_filter_dropdown.value = "ALL"
        self.min_amount.value = ""
        self.max_amount.value = ""
        self.start_date.value = ""
        self.end_date.value = ""
        self.current_page = 1
        self.update_data()

    def update_data(self, type_filter="ALL", start_date=None, end_date=None, min_amount=None, max_amount=None, search_query=None, wallet_filter="ALL", fee_filter="ALL"):
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
                fee_filter=fee_filter
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
                fee_filter=fee_filter
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
            
            # Wallet badge - gradient styled
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

            # Alternate row background color
            row_color = ft.Colors.with_opacity(0.04, ft.Colors.WHITE) if idx % 2 != 0 else ft.Colors.TRANSPARENT

            self.data_table.rows.append(
                ft.DataRow(
                    color=row_color,
                    cells=[
                        ft.DataCell(ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M'), color=ft.Colors.WHITE70)),
                        ft.DataCell(ft.Text(tx.type.value, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)),
                        wallet_cell,
                        ft.DataCell(ft.Text(f"{tx.amount:,.2f} EGP", color=amount_color, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(fee_text, color=fee_color, weight=ft.FontWeight.BOLD if fee > 0 else ft.FontWeight.NORMAL, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(f"{tx.balance_after:,.2f} EGP" if tx.balance_after >= 0 else "N/A", color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(tx.counterpart or "—", color=ft.Colors.WHITE70)),
                    ]
                )
            )
        
        self.flet_page.update()
