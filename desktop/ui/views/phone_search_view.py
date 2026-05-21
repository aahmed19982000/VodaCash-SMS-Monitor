# desktop/ui/views/phone_search_view.py
import flet as ft
from desktop.db.database import DesktopDatabase
from typing import List

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

class PhoneSearchView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        # Title Control
        self.title_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                ft.Text("Phone Search / البحث برقم الهاتف", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Search Control
        self.search_field = ft.TextField(
            label="ابحث برقم الهاتف أو الاسم / Search by Phone or Name",
            hint_text="أدخل رقم الهاتف أو الاسم للبحث الفوري...",
            prefix_icon=ft.Icons.PHONE_ANDROID_ROUNDED,
            width=450,
            border_radius=12,
            on_change=self.on_search_change,
            on_submit=self.on_search_change,
            text_align=ft.TextAlign.LEFT,
            filled=True,
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
        )

        self.clear_btn = ft.IconButton(
            icon=ft.Icons.CLEAR_ROUNDED,
            icon_color=ft.Colors.WHITE60,
            tooltip="مسح البحث",
            on_click=self.clear_search,
        )

        self.status_label = ft.Text("", color=ft.Colors.WHITE54, size=14)
        self.total_txs_text = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
        self.received_text = ft.Text("0.00 EGP", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.sent_text = ft.Text("0.00 EGP", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.net_flow_text = ft.Text("0.00 EGP", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

        self.kpi_row = ft.Row(
            controls=[
                self._build_kpi_card("إجمالي العمليات / Total TXs", self.total_txs_text, ft.Icons.SYNC_ALT_ROUNDED, ft.Colors.BLUE_GREY_900, ft.Colors.BLUE_400),
                self._build_kpi_card("إجمالي المستلم / Received", self.received_text, ft.Icons.ARROW_DOWNWARD_ROUNDED, ft.Colors.GREEN_900, ft.Colors.GREEN_400),
                self._build_kpi_card("إجمالي المرسل / Sent", self.sent_text, ft.Icons.ARROW_UPWARD_ROUNDED, ft.Colors.RED_900, ft.Colors.RED_400),
                self._build_kpi_card("صافي التدفق / Net Flow", self.net_flow_text, ft.Icons.MONEY_ROUNDED, ft.Colors.BLACK38, ft.Colors.AMBER_400),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
            visible=False
        )

        # DataTable
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date & Time")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Wallet")),
                ft.DataColumn(ft.Text("Amount (EGP)", text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("Balance (EGP)", text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("Counterpart")),
                ft.DataColumn(ft.Text("SMS Content", text_align=ft.TextAlign.CENTER)),
            ],
            rows=[],
            expand=True,
            heading_row_color=ft.Colors.BLACK26,
            vertical_lines=ft.BorderSide(1, ft.Colors.WHITE10),
            horizontal_lines=ft.BorderSide(1, ft.Colors.WHITE10),
        )

        # Table container with scrollable functionality
        self.table_scroll_container = ft.Column([self.data_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.table_container = ft.Container(
            content=self.table_scroll_container,
            expand=True,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=10,
            visible=False
        )

        # Empty state panel
        self.empty_state = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON_SEARCH_OUTLINED, size=80, color=ft.Colors.WHITE24),
                    ft.Text("ابدأ بكتابة رقم الهاتف أو الاسم في شريط البحث لعرض المعاملات فوراً", color=ft.Colors.WHITE54, size=16, text_align=ft.TextAlign.CENTER),
                    ft.Text("Start typing a phone number or contact name above to search", color=ft.Colors.WHITE30, size=12, text_align=ft.TextAlign.CENTER)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            alignment=ft.alignment.Alignment.CENTER,
            padding=40,
            expand=True
        )

        # No results state panel
        self.no_results_state = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=80, color=ft.Colors.RED_300),
                    ft.Text("لم يتم العثور على أي معاملات مرتبطة بهذا الرقم", color=ft.Colors.WHITE54, size=16, text_align=ft.TextAlign.CENTER),
                    ft.Text("No transactions found for the specified query", color=ft.Colors.WHITE30, size=12, text_align=ft.TextAlign.CENTER)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            alignment=ft.alignment.Alignment.CENTER,
            padding=40,
            expand=True,
            visible=False
        )

        # Main Layout
        self.content = ft.Column(
            controls=[
                self.title_row,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                
                # Search Bar Row
                ft.Row(
                    controls=[
                        self.search_field,
                        self.clear_btn,
                        self.status_label
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                
                ft.Divider(height=15, color=ft.Colors.WHITE24),
                
                # KPIs
                self.kpi_row,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                # Dynamic content area
                self.empty_state,
                self.no_results_state,
                self.table_container
            ],
            expand=True
        )

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, bg_color: str, accent_color: str):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, color=accent_color, size=18), ft.Text(title, color=ft.Colors.WHITE54, size=12)], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=8, color=ft.Colors.WHITE10),
                    text_control
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            width=220,
            height=100,
            bgcolor=bg_color,
            border_radius=12,
            padding=10,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, accent_color)),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color=ft.Colors.BLACK38),
            scale=1.0,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._handle_card_hover
        )

    def _handle_card_hover(self, e):
        e.control.scale = 1.03 if e.data == "true" else 1.0
        e.control.update()

    def on_search_change(self, e):
        self.update_data()

    def clear_search(self, e):
        self.search_field.value = ""
        self.update_data()

    def show_sms_dialog(self, tx):
        def close_dialog(e):
            dialog.open = False
            self.flet_page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("تفاصيل الرسالة النصية / SMS Details"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("نص الرسالة الأصلي (Raw SMS):", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                        ft.Container(
                            content=ft.Text(tx.raw_sms, size=14, selectable=True),
                            padding=15,
                            bgcolor=ft.Colors.BLACK12,
                            border_radius=8,
                            border=ft.Border.all(1, ft.Colors.WHITE10),
                            width=500,
                        ),
                        ft.Divider(height=15),
                        ft.Row(
                            controls=[
                                ft.Text("رقم المعاملة (TX ID):", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(tx.transaction_id, size=12, selectable=True),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("توقيت الاستلام:", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M:%S'), size=12),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("نسبة التأكيد (Confidence):", weight=ft.FontWeight.BOLD, size=12),
                                ft.Text(f"{tx.confidence:.0%}", size=12, color=ft.Colors.GREEN_400 if tx.confidence >= 0.8 else ft.Colors.AMBER_400),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                    ],
                    tight=True,
                    spacing=10
                ),
                width=500
            ),
            actions=[
                ft.TextButton("إغلاق / Close", on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.flet_page.dialog = dialog
        dialog.open = True
        self.flet_page.update()

    def update_data(self):
        query = self.search_field.value.strip() if self.search_field.value else ""
        if not query:
            self.status_label.value = ""
            self.empty_state.visible = True
            self.no_results_state.visible = False
            self.kpi_row.visible = False
            self.table_container.visible = False
            self.flet_page.update()
            return

        try:
            txs = self.db.get_transactions_by_counterpart(query)
        except Exception as ex:
            print(f"Error searching transactions: {ex}")
            txs = []

        if not txs:
            self.status_label.value = "لم يتم العثور على نتائج / No results found"
            self.empty_state.visible = False
            self.no_results_state.visible = True
            self.kpi_row.visible = False
            self.table_container.visible = False
            self.flet_page.update()
            return

        # Slice results to 100 for high performance
        total_found = len(txs)
        if total_found > 100:
            self.status_label.value = f"تم العثور على {total_found} معاملة (يعرض آخر 100) / Found {total_found} txs (showing latest 100)"
            txs = txs[:100]
        else:
            self.status_label.value = f"تم العثور على {total_found} معاملة / Found {total_found} txs"

        # We have transactions! Calculate KPIs
        total_txs = len(txs)
        total_received = 0.0
        total_sent = 0.0

        for tx in txs:
            if tx.type.value == "RECEIVED":
                total_received += tx.amount
            elif tx.type.value in ["SENT", "BILL", "PURCHASE", "TOPUP"]:
                total_sent += tx.amount

        net_flow = total_received - total_sent

        # Update KPI texts
        self.total_txs_text.value = str(total_txs)
        self.received_text.value = f"+{total_received:,.2f} EGP"
        self.sent_text.value = f"-{total_sent:,.2f} EGP"
        
        # Color code net flow
        if net_flow > 0:
            self.net_flow_text.value = f"+{net_flow:,.2f} EGP"
            self.net_flow_text.color = ft.Colors.GREEN_400
        elif net_flow < 0:
            self.net_flow_text.value = f"{net_flow:,.2f} EGP"
            self.net_flow_text.color = ft.Colors.RED_400
        else:
            self.net_flow_text.value = "0.00 EGP"
            self.net_flow_text.color = ft.Colors.WHITE

        # Update table rows
        self.data_table.rows.clear()
        for tx in txs:
            amount_color = ft.Colors.GREEN_400 if tx.type.value == "RECEIVED" else ft.Colors.RED_400
            
            # Wallet badge
            w_info = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
            w_colors = w_info["colors"]
            wallet_cell = ft.DataCell(
                ft.Container(
                    content=ft.Text(w_info["name"], size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    gradient=ft.LinearGradient(colors=w_colors),
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                    border_radius=5,
                )
            )

            # Action cell with View SMS button
            action_cell = ft.DataCell(
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.FEED_OUTLINED,
                        icon_color=ft.Colors.BLUE_400,
                        tooltip="عرض تفاصيل الرسالة",
                        on_click=lambda e, t=tx: self.show_sms_dialog(t)
                    ),
                    alignment=ft.alignment.Alignment.CENTER
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
                        action_cell,
                    ]
                )
            )

        # Set visibilities
        self.empty_state.visible = False
        self.no_results_state.visible = False
        self.kpi_row.visible = True
        self.table_container.visible = True
        self.flet_page.update()
