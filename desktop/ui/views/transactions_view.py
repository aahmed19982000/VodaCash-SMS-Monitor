# desktop/ui/views/transactions_view.py
import flet as ft
from desktop.db.database import DesktopDatabase

WALLET_BADGES = {
    "vodafone_cash": {"name": "Vodafone Cash", "color": "#990000"},
    "orange_cash": {"name": "Orange Cash", "color": "#CC5200"},
    "etisalat_cash": {"name": "Etisalat Cash", "color": "#5A8F18"},
    "we_pay": {"name": "WE Pay", "color": "#351C49"},
    "instapay": {"name": "InstaPay", "color": "#005A70"},
    "bank": {"name": "Bank Account", "color": "#0F4C5C"},
    "unspecified": {"name": "Unspecified", "color": "#4E6E5D"},
}

class TransactionsView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        self.search_field = ft.TextField(
            label="Search (Number, Text...)",
            width=220,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.apply_filters
        )
        
        # Filter Controls
        self.type_dropdown = ft.Dropdown(
            label="Type",
            width=130,
            options=[
                ft.dropdown.Option("ALL"),
                ft.dropdown.Option("RECEIVED"),
                ft.dropdown.Option("SENT"),
                ft.dropdown.Option("BILL"),
                ft.dropdown.Option("PURCHASE"),
                ft.dropdown.Option("TOPUP"),
            ],
            value="ALL",
            on_select=self.apply_filters
        )

        self.wallet_dropdown = ft.Dropdown(
            label="Wallet",
            width=150,
            options=[
                ft.dropdown.Option("ALL"),
                ft.dropdown.Option("vodafone_cash", "Vodafone Cash"),
                ft.dropdown.Option("orange_cash", "Orange Cash"),
                ft.dropdown.Option("etisalat_cash", "Etisalat Cash"),
                ft.dropdown.Option("we_pay", "WE Pay"),
                ft.dropdown.Option("instapay", "InstaPay"),
                ft.dropdown.Option("bank", "Bank Account"),
                ft.dropdown.Option("unspecified", "Unspecified"),
            ],
            value="ALL",
            on_select=self.apply_filters
        )
        
        self.min_amount = ft.TextField(label="Min Amount", width=100, keyboard_type=ft.KeyboardType.NUMBER, on_submit=self.apply_filters)
        self.max_amount = ft.TextField(label="Max Amount", width=100, keyboard_type=ft.KeyboardType.NUMBER, on_submit=self.apply_filters)
        
        self.start_date = ft.TextField(label="Start Date (YYYY-MM-DD)", width=170, on_submit=self.apply_filters)
        self.end_date = ft.TextField(label="End Date (YYYY-MM-DD)", width=170, on_submit=self.apply_filters)

        self.btn_filter = ft.ElevatedButton("Apply Filters", on_click=self.apply_filters, icon=ft.Icons.FILTER_ALT)
        self.btn_clear = ft.OutlinedButton("Clear", on_click=self.clear_filters, icon=ft.Icons.CLEAR)

        # DataTable
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date & Time")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Wallet")),
                ft.DataColumn(ft.Text("Amount (EGP)", text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("Balance (EGP)", text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("Counterpart")),
            ],
            rows=[],
            expand=True,
            heading_row_color=ft.Colors.BLACK26,
            vertical_lines=ft.BorderSide(1, ft.Colors.WHITE10),
            horizontal_lines=ft.BorderSide(1, ft.Colors.WHITE10),
        )

        # Scrollable container for the table
        self.table_container = ft.Column([self.data_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

        self.content = ft.Column(
            controls=[
                ft.Text("Transactions Archive", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                # Filters Row
                ft.Row(
                    controls=[
                        self.search_field,
                        self.type_dropdown,
                        self.wallet_dropdown,
                        self.min_amount,
                        self.max_amount,
                        self.start_date,
                        self.end_date,
                        self.btn_filter,
                        self.btn_clear
                    ],
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                
                ft.Divider(height=20, color=ft.Colors.WHITE24),
                
                # Table
                ft.Container(
                    content=self.table_container,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                )
            ]
        )

    def apply_filters(self, e=None):
        search_val = self.search_field.value if self.search_field.value else None
        min_val = float(self.min_amount.value) if self.min_amount.value else None
        max_val = float(self.max_amount.value) if self.max_amount.value else None
        start = self.start_date.value if self.start_date.value else None
        end = self.end_date.value if self.end_date.value else None
        type_val = self.type_dropdown.value
        wallet_val = self.wallet_dropdown.value

        self.update_data(
            type_filter=type_val,
            start_date=start,
            end_date=end,
            min_amount=min_val,
            max_amount=max_val,
            search_query=search_val,
            wallet_filter=wallet_val
        )

    def clear_filters(self, e=None):
        self.search_field.value = ""
        self.type_dropdown.value = "ALL"
        self.wallet_dropdown.value = "ALL"
        self.min_amount.value = ""
        self.max_amount.value = ""
        self.start_date.value = ""
        self.end_date.value = ""
        self.update_data()

    def update_data(self, type_filter="ALL", start_date=None, end_date=None, min_amount=None, max_amount=None, search_query=None, wallet_filter="ALL"):
        """تحديث بيانات الجدول مع الفلاتر"""
        try:
            txs = self.db.get_all_transactions(
                type_filter=type_filter,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search_query=search_query,
                wallet_filter=wallet_filter
            )
        except Exception as ex:
            print(f"Error fetching filtered data: {ex}")
            txs = []

        self.data_table.rows.clear()
        for tx in txs:
            amount_color = ft.Colors.GREEN_400 if tx.type.value == "RECEIVED" else ft.Colors.RED_400
            
            # Wallet badge
            w_info = WALLET_BADGES.get(tx.wallet_id, WALLET_BADGES["unspecified"])
            wallet_cell = ft.DataCell(
                ft.Container(
                    content=ft.Text(w_info["name"], size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=w_info["color"],
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                    border_radius=5,
                )
            )

            self.data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M'))),
                        ft.DataCell(ft.Text(tx.type.value, weight=ft.FontWeight.BOLD)),
                        wallet_cell,
                        ft.DataCell(ft.Text(f"{tx.amount:,.2f}", color=amount_color, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(f"{tx.balance_after:,.2f}" if tx.balance_after >= 0 else "N/A", text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(tx.counterpart)),
                    ]
                )
            )
        
        self.flet_page.update()
