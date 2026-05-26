# desktop/ui/views/phone_search_view.py
import flet as ft
from desktop.db.database import DesktopDatabase
from typing import List

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
            label="Search by Phone or Name / ابحث برقم الهاتف أو الاسم",
            hint_text="Type phone number or contact name...",
            prefix_icon=ft.Icons.PERSON_SEARCH_ROUNDED,
            width=450,
            border_radius=12,
            on_change=self.on_search_change,
            on_submit=self.on_search_change,
            text_align=ft.TextAlign.LEFT,
            filled=True,
            bgcolor="#0B0F19",
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
                self._build_kpi_card("إجمالي العمليات / Total TXs", self.total_txs_text, ft.Icons.SYNC_ALT_ROUNDED, ["#06152B", "#020714"], ft.Colors.BLUE_400),
                self._build_kpi_card("إجمالي المستلم / Received", self.received_text, ft.Icons.ARROW_DOWNWARD_ROUNDED, ["#081C15", "#040E0B"], ft.Colors.GREEN_400),
                self._build_kpi_card("إجمالي المرسل / Sent", self.sent_text, ft.Icons.ARROW_UPWARD_ROUNDED, ["#1F080C", "#0E0305"], ft.Colors.RED_400),
                self._build_kpi_card("صافي التدفق / Net Flow", self.net_flow_text, ft.Icons.MONEY_ROUNDED, ["#1C160C", "#0B0A07"], ft.Colors.AMBER_400),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
            visible=False
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
                ft.DataColumn(ft.Text("SMS / تفاصيل", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
            ],
            rows=[],
            expand=True,
            heading_row_color="#0B0F19",
            vertical_lines=ft.BorderSide(1, ft.Colors.WHITE10),
            horizontal_lines=ft.BorderSide(1, ft.Colors.WHITE10),
        )

        # Table container with scrollable functionality
        self.table_scroll_container = ft.Column([self.data_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.table_container = ft.Container(
            content=self.table_scroll_container,
            expand=True,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=15,
            bgcolor=ft.Colors.BLACK26,
            padding=10,
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

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, gradient_colors: list, accent_color: str):
        title_parts = title.split(" / ")
        title_en = title_parts[1] if len(title_parts) > 1 else title
        title_ar = title_parts[0] if len(title_parts) > 0 else ""

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, color=accent_color, size=18),
                                bgcolor=ft.Colors.with_opacity(0.12, accent_color),
                                padding=6,
                                border_radius=15,
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
            width=220,
            height=110,
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
        accent_color = e.control.border.top.color
        if e.data == "true":
            e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=16, color=ft.Colors.with_opacity(0.15, accent_color))
        else:
            e.control.shadow = ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK))
        e.control.update()

    def on_search_change(self, e):
        self.update_data()

    def clear_search(self, e):
        self.search_field.value = ""
        self.update_data()

    def show_sms_dialog(self, tx):
        def close_dialog(e):
            self.flet_page.close_dialog_overlay(custom_dlg)

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
                                ft.Icon(ft.Icons.FEED_OUTLINED, color=ft.Colors.BLUE_ACCENT, size=24),
                                ft.Text("تفاصيل الرسالة النصية / SMS Details", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Text("نص الرسالة الأصلي (Raw SMS):", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT, size=13),
                        ft.Container(
                            content=ft.Text(tx.raw_sms, size=13, selectable=True, color=ft.Colors.WHITE),
                            padding=15,
                            bgcolor="#0B0F19",
                            border_radius=10,
                            border=ft.Border.all(1, ft.Colors.WHITE10),
                            width=500,
                        ),
                        ft.Divider(height=15, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.Text("رقم المعاملة (TX ID):", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE70),
                                ft.Text(tx.transaction_id, size=12, selectable=True, weight=ft.FontWeight.W_500),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text(f"{phone_label}:", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE70),
                                ft.Text(tx.counterpart or "—", size=12, selectable=True, weight=ft.FontWeight.W_500),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("توقيت الاستلام:", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE70),
                                ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M:%S'), size=12, weight=ft.FontWeight.W_500),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("نسبة التأكيد (Confidence):", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE70),
                                ft.Text(f"{tx.confidence:.0%}", size=12, color=ft.Colors.GREEN_400 if tx.confidence >= 0.8 else ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.TextButton("إغلاق / Close", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_ACCENT))
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        )
                    ],
                    tight=True,
                    spacing=10
                ),
                bgcolor="#080C14",
                border_radius=18,
                padding=20,
                width=540,
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
            txs = self.db.get_transactions_by_counterpart(query, limit=101)
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

        # Check if more than 100 results exist
        total_found = len(txs)
        if total_found > 100:
            self.status_label.value = "تم العثور على أكثر من 100 معاملة (يعرض آخر 100) / Found more than 100 txs (showing latest 100)"
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
        
        for idx, tx in enumerate(txs):
            amount_color = ft.Colors.GREEN_400 if tx.type.value == "RECEIVED" else ft.Colors.RED_400
            
            # Wallet badge - gradient styled
            w_info = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
            w_colors = w_info["colors"]
            wallet_cell = ft.DataCell(
                ft.Container(
                    content=ft.Text(w_info["name"], size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    gradient=ft.LinearGradient(colors=w_colors),
                    padding=ft.Padding(left=10, top=5, right=10, bottom=5),
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.2, w_info.get("accent_color", "#64748B")))
                )
            )

            # Action cell with View SMS button styled nicely
            action_cell = ft.DataCell(
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.FEED_OUTLINED,
                        icon_color=ft.Colors.BLUE_ACCENT,
                        icon_size=18,
                        tooltip="عرض تفاصيل الرسالة",
                        on_click=lambda e, t=tx: self.show_sms_dialog(t)
                    ),
                    alignment=ft.alignment.Alignment.CENTER
                )
            )

            fee = self.db.calculate_fee(tx)
            fee_color = ft.Colors.AMBER_400 if fee > 0 else ft.Colors.WHITE38
            fee_text = f"+{fee:,.2f}" if fee > 0 else "-"

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
                        ft.DataCell(ft.Text(f"{tx.balance_after:,.2f} EGP" if tx.balance_after >= 0 else "N/A", color=ft.Colors.WHITE70, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.RIGHT)),
                        ft.DataCell(ft.Text(cp, color=ft.Colors.WHITE70)),
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
