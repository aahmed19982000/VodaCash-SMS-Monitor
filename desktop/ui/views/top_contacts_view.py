# desktop/ui/views/top_contacts_view.py
import flet as ft
from desktop.db.database import DesktopDatabase
from datetime import datetime

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

class TopContactsView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        # Title
        self.title_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.PEOPLE_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                ft.Text("Top Contacts / الأكثر تفاعلاً", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Consistent Input styling helper
        input_style = {
            "border_radius": 12,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": ft.Colors.BLUE_ACCENT,
            "filled": True
        }

        # Filters Controls
        self.search_field = ft.TextField(
            label="بحث بالاسم أو الرقم / Search Name or Phone",
            hint_text="ابحث هنا...",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            width=240,
            on_submit=self.apply_filters,
            **input_style
        )

        self.sort_dropdown = ft.Dropdown(
            label="ترتيب حسب / Sort By",
            width=180,
            options=[
                ft.dropdown.Option("count", "عدد العمليات / Tx Count"),
                ft.dropdown.Option("received", "إجمالي الوارد / Received"),
                ft.dropdown.Option("sent", "إجمالي الصادر / Sent"),
                ft.dropdown.Option("net_flow", "صافي التدفق / Net Flow"),
            ],
            value="count",
            on_select=self.apply_filters,
            **input_style
        )

        self.limit_dropdown = ft.Dropdown(
            label="العدد الأقصى / Limit",
            width=130,
            options=[
                ft.dropdown.Option("5", "أفضل 5 / Top 5"),
                ft.dropdown.Option("10", "أفضل 10 / Top 10"),
                ft.dropdown.Option("25", "أفضل 25 / Top 25"),
                ft.dropdown.Option("50", "أفضل 50 / Top 50"),
                ft.dropdown.Option("100", "أفضل 100 / Top 100"),
                ft.dropdown.Option("0", "الكل / All"),
            ],
            value="10",
            on_select=self.apply_filters,
            **input_style
        )

        self.start_date = ft.TextField(
            label="تاريخ البداية (YYYY-MM-DD)",
            hint_text="مثال: 2026-05-01",
            width=170,
            on_submit=self.apply_filters,
            **input_style
        )

        self.end_date = ft.TextField(
            label="تاريخ النهاية (YYYY-MM-DD)",
            hint_text="مثال: 2026-05-31",
            width=170,
            on_submit=self.apply_filters,
            **input_style
        )

        self.btn_filter = ft.ElevatedButton(
            "تطبيق / Apply",
            on_click=self.apply_filters,
            icon=ft.Icons.FILTER_ALT,
            bgcolor="#0F3C6D",
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(15, 18, 15, 18),
            )
        )
        
        self.btn_clear = ft.OutlinedButton(
            "تفريغ / Clear",
            on_click=self.clear_filters,
            icon=ft.Icons.CLEAR,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(15, 18, 15, 18),
            )
        )

        # Filters Row
        self.filters_row = ft.Row(
            controls=[
                self.search_field,
                self.sort_dropdown,
                self.limit_dropdown,
                self.start_date,
                self.end_date,
                self.btn_filter,
                self.btn_clear
            ],
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # KPI Stats for the filtered list
        self.total_contacts_badge = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.total_received_badge = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.total_sent_badge = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)

        self.kpi_container = ft.Container(
            content=ft.Row(
                controls=[
                    self._build_kpi_card("Total Contacts / إجمالي جهات الاتصال", self.total_contacts_badge, ft.Icons.PEOPLE_OUTLINE, ["#06152B", "#020714"], ft.Colors.BLUE_400),
                    self._build_kpi_card("Total Received / إجمالي الوارد المعروض", self.total_received_badge, ft.Icons.CALL_RECEIVED, ["#081C15", "#040E0B"], ft.Colors.GREEN_400),
                    self._build_kpi_card("Total Sent / إجمالي الصادر المعروض", self.total_sent_badge, ft.Icons.CALL_MADE, ["#1F080C", "#0E0305"], ft.Colors.RED_400),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=20,
                wrap=True
            ),
            margin=ft.Margin(0, 5, 0, 15)
        )

        # Cards Layout Container
        self.cards_row = ft.Row(wrap=True, spacing=15)
        self.scrollable_container = ft.Column(
            controls=[self.cards_row],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        )

        # Empty State
        self.empty_state = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=80, color=ft.Colors.WHITE24),
                    ft.Text("لا يوجد جهات اتصال متفاعلة في هذه الفترة", color=ft.Colors.WHITE54, size=16),
                    ft.Text("No active contacts found for this query", color=ft.Colors.WHITE30, size=12)
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

        self.content = ft.Column(
            controls=[
                self.title_row,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                self.filters_row,
                ft.Divider(height=15, color=ft.Colors.WHITE24),
                self.kpi_container,
                ft.Container(
                    content=self.scrollable_container,
                    expand=True,
                ),
                self.empty_state
            ],
            expand=True
        )

    def _build_kpi_card(self, title: str, text_control: ft.Text, icon: str, gradient_colors: list, accent_color: str, width: int = 240):
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
            on_hover=self._handle_kpi_card_hover
        )

    def _handle_kpi_card_hover(self, e):
        e.control.scale = 1.04 if e.data == "true" else 1.0
        accent_color = e.control.border.top.color
        if e.data == "true":
            e.control.border = ft.Border.all(1, ft.Colors.with_opacity(0.4, accent_color))
            e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=16, color=ft.Colors.with_opacity(0.25, accent_color))
        else:
            e.control.border = ft.Border.all(1, ft.Colors.with_opacity(0.18, accent_color))
            e.control.shadow = ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK))
        e.control.update()

    def apply_filters(self, e=None):
        self.update_data()

    def clear_filters(self, e=None):
        self.search_field.value = ""
        self.sort_dropdown.value = "count"
        self.limit_dropdown.value = "10"
        self.start_date.value = ""
        self.end_date.value = ""
        self.update_data()

    def _handle_card_hover(self, e):
        e.control.scale = 1.04 if e.data == "true" else 1.0
        if e.data == "true":
            e.control.border = ft.Border.all(1, ft.Colors.with_opacity(0.4, ft.Colors.BLUE_ACCENT))
            e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=16, color=ft.Colors.with_opacity(0.2, ft.Colors.BLUE_ACCENT))
        else:
            e.control.border = ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT))
            e.control.shadow = ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK))
        e.control.update()

    def update_data(self):
        # Fetch configurations
        search = self.search_field.value.strip() if self.search_field.value else None
        sort = self.sort_dropdown.value
        limit_val = int(self.limit_dropdown.value)
        start = self.start_date.value.strip() if self.start_date.value else None
        end = self.end_date.value.strip() if self.end_date.value else None

        # Fetch from database
        try:
            contacts = self.db.get_top_contacts(
                start_date=start,
                end_date=end,
                search_query=search,
                sort_by=sort,
                limit=limit_val
            )
        except Exception as ex:
            print(f"Error fetching top contacts: {ex}")
            contacts = []

        if not contacts:
            self.empty_state.visible = True
            self.scrollable_container.visible = False
            self.total_contacts_badge.value = "0"
            self.total_received_badge.value = "0.00 EGP"
            self.total_sent_badge.value = "0.00 EGP"
            self.flet_page.update()
            return

        self.empty_state.visible = False
        self.scrollable_container.visible = True

        # Calculate totals
        total_rec = sum(c["total_received"] for c in contacts)
        total_snt = sum(c["total_sent"] for c in contacts)
        
        self.total_contacts_badge.value = str(len(contacts))
        self.total_received_badge.value = f"+{total_rec:,.2f} EGP"
        self.total_sent_badge.value = f"-{total_snt:,.2f} EGP"

        # Build cards
        new_cards = []
        for c in contacts:
            counterpart = c["counterpart"]
            tx_count = c["transaction_count"]
            received = c["total_received"]
            sent = c["total_sent"]
            net = c["net_flow"]

            # Visual color code for net flow
            if net > 0:
                net_text = f"+{net:,.2f}"
                net_color = ft.Colors.GREEN_400
            elif net < 0:
                net_text = f"{net:,.2f}"
                net_color = ft.Colors.RED_400
            else:
                net_text = "0.00"
                net_color = ft.Colors.WHITE

            # Contact initial for avatar
            avatar_letter = counterpart[0].upper() if counterpart else "?"

            # Neon glowing gradient avatar
            avatar = ft.Container(
                content=ft.Text(avatar_letter, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=14),
                gradient=ft.LinearGradient(
                    colors=[ft.Colors.INDIGO_ACCENT, ft.Colors.PURPLE_ACCENT],
                    begin=ft.alignment.Alignment.TOP_LEFT,
                    end=ft.alignment.Alignment.BOTTOM_RIGHT
                ),
                shape=ft.BoxShape.CIRCLE,
                width=38,
                height=38,
                alignment=ft.alignment.Alignment.CENTER,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=6, color=ft.Colors.with_opacity(0.3, ft.Colors.INDIGO_ACCENT))
            )

            card = ft.Container(
                content=ft.Column(
                    controls=[
                        # Header Row
                        ft.Row(
                            controls=[
                                avatar,
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            counterpart,
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.WHITE,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            width=140
                                        ),
                                        ft.Text(f"{tx_count} TXs / عملية", size=11, color=ft.Colors.BLUE_200, weight=ft.FontWeight.W_500)
                                    ],
                                    spacing=1,
                                    expand=True
                                )
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        
                        # Financial Flow List
                        ft.Row(
                            controls=[
                                ft.Text("الوارد / Received:", size=11, color=ft.Colors.WHITE54),
                                ft.Text(f"+{received:,.2f}", size=11, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            controls=[
                                ft.Text("الصادر / Sent:", size=11, color=ft.Colors.WHITE54),
                                ft.Text(f"-{sent:,.2f}", size=11, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(height=8, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.Text("الصافي / Net Flow:", size=11, color=ft.Colors.WHITE54, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{net_text}", size=12, color=net_color, weight=ft.FontWeight.BOLD)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ],
                    spacing=6,
                ),
                width=240,
                height=160,
                gradient=ft.LinearGradient(
                    colors=["#1E293B", "#0F172A"],
                    begin=ft.alignment.Alignment.TOP_LEFT,
                    end=ft.alignment.Alignment.BOTTOM_RIGHT
                ),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_ACCENT)),
                border_radius=16,
                padding=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)),
                scale=1.0,
                animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                on_hover=self._handle_card_hover,
                on_click=lambda e, cp=counterpart: self.show_contact_details(cp)
            )
            new_cards.append(card)

        self.cards_row.controls = new_cards
        self.flet_page.update()

    def show_contact_details(self, counterpart: str):
        """عرض تفاصيل المعاملات مع هذا الرقم في AlertDialog مخصص"""
        try:
            txs = self.db.get_transactions_by_counterpart(counterpart, limit=200)
        except Exception as e:
            print(f"Error loading transactions for {counterpart}: {e}")
            txs = []

        def close_dialog(e):
            self.flet_page.close_dialog_overlay(details_overlay)

        def view_sms_content(tx_item):
            def close_sms_dialog(e):
                self.flet_page.close_dialog_overlay(sms_overlay)

            tx_type_str = tx_item.type.value if hasattr(tx_item.type, "value") else str(tx_item.type)
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

            sms_overlay = ft.Container(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SMS_OUTLINED, color=ft.Colors.BLUE_ACCENT, size=24),
                                    ft.Text("تفاصيل الرسالة النصية / SMS Details", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE),
                                ],
                                spacing=10,
                            ),
                            ft.Divider(height=10, color=ft.Colors.WHITE10),
                            ft.Text("نص الرسالة الأصلي (Raw SMS):", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT, size=13),
                            ft.Container(
                                content=ft.Text(tx_item.raw_sms, size=13, selectable=True, color=ft.Colors.WHITE),
                                padding=15,
                                bgcolor="#0B0F19",
                                border_radius=10,
                                border=ft.Border.all(1, ft.Colors.WHITE10),
                                width=450,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(f"{phone_label}:", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE70),
                                    ft.Text(tx_item.counterpart or "—", size=12, selectable=True, weight=ft.FontWeight.W_500),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Divider(height=10, color=ft.Colors.WHITE10),
                            ft.Row(
                                controls=[
                                    ft.TextButton("إغلاق / Close", on_click=close_sms_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_ACCENT))
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
                    width=480,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                ),
                alignment=ft.alignment.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
                left=0,
                top=0,
                right=0,
                bottom=0,
            )
            
            self.flet_page.show_dialog_overlay(sms_overlay)

        tx_list = ft.ListView(expand=True, spacing=10, height=350)
        
        for tx in txs:
            is_recv = tx.type.value == "RECEIVED"
            amt_color = ft.Colors.GREEN_400 if is_recv else ft.Colors.RED_400
            prefix = "+" if is_recv else "-"
            icon_name = ft.Icons.CALL_RECEIVED if is_recv else ft.Icons.CALL_MADE

            w_style = WALLET_STYLING.get(tx.wallet_id, WALLET_STYLING["unspecified"])
            w_name = w_style["name"]
            w_colors = w_style["colors"]

            fee = self.db.calculate_fee(tx)
            fee_str = f" | Profit: {fee:.2f} EGP" if fee > 0 else ""

            tx_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon_name, color=amt_color, size=18),
                            ft.Column(
                                controls=[
                                    ft.Text(f"{tx.type.value} — {prefix}{tx.amount:,.2f} EGP{fee_str}", weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.WHITE),
                                    ft.Text(tx.sms_timestamp.strftime('%Y-%m-%d %H:%M'), size=11, color=ft.Colors.WHITE54)
                                ],
                                spacing=2,
                                expand=True
                            ),
                            ft.Container(
                                content=ft.Text(w_name, size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                gradient=ft.LinearGradient(colors=w_colors),
                                padding=ft.Padding(6, 3, 6, 3),
                                border_radius=4,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SMS_OUTLINED,
                                icon_size=16,
                                tooltip="عرض الرسالة",
                                on_click=lambda e, t=tx: view_sms_content(t)
                            )
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    padding=8,
                    bgcolor="#0B0F19",
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.WHITE10)
                )
            )

        details_overlay = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(f"تفاصيل العمليات: {counterpart} / Transactions", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text(f"إجمالي العمليات: {len(txs)} / Total Transactions", size=13, color=ft.Colors.WHITE70),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        tx_list,
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.TextButton("إغلاق / Close", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.WHITE54))
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        )
                    ],
                    tight=True,
                    spacing=12,
                ),
                bgcolor="#0B0F19",
                border_radius=18,
                padding=20,
                width=550,
                border=ft.Border.all(1, ft.Colors.WHITE10),
            ),
            alignment=ft.alignment.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            left=0,
            top=0,
            right=0,
            bottom=0,
        )

        self.flet_page.show_dialog_overlay(details_overlay)
