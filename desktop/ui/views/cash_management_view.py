# desktop/ui/views/cash_management_view.py
# ── صفحة إدارة النقدية والأرباح ─────────────────────────────────────────

import flet as ft
from datetime import datetime
from desktop.db.database import DesktopDatabase

ENTRY_TYPES = {
    "CASH_IN":    {"label": "نقدية داخلة 💵",  "color": "#22C55E", "icon": ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED},
    "PROFIT_IN":  {"label": "ربح نقدي 🟡",     "color": "#F59E0B", "icon": ft.Icons.PERCENT_ROUNDED},
    "CASH_OUT":   {"label": "نقدية خارجة 📤",  "color": "#EF4444", "icon": ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED},
    "EXPENSE":    {"label": "مصروف/مدفوعات 🧾", "color": "#A855F7", "icon": ft.Icons.RECEIPT_LONG_ROUNDED},
}

AR_LABELS = {
    "CASH_IN":   "نقدية داخلة",
    "PROFIT_IN": "ربح نقدي",
    "CASH_OUT":  "نقدية خارجة",
    "EXPENSE":   "مصروف",
}


class CashManagementView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20
        self.current_page = 1
        self.page_size = 30

        # ── إدخال حركة جديدة ──────────────────────────────────────────
        input_style = {
            "border_radius": 12,
            "bgcolor": "#0B0F19",
            "border_color": ft.Colors.WHITE24,
            "focused_border_color": ft.Colors.BLUE_ACCENT,
            "filled": True,
        }

        self.type_dropdown = ft.Dropdown(
            label="النوع / Type",
            width=200,
            options=[
                ft.dropdown.Option(k, v["label"]) for k, v in ENTRY_TYPES.items()
            ],
            value="CASH_IN",
            **input_style,
        )
        self.amount_field = ft.TextField(
            label="المبلغ (EGP) / Amount",
            width=160,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._add_entry,
            **input_style,
        )
        self.desc_field = ft.TextField(
            label="وصف / Description",
            width=300,
            on_submit=self._add_entry,
            **input_style,
        )
        self.btn_add = ft.ElevatedButton(
            "إضافة / Add",
            icon=ft.Icons.ADD_ROUNDED,
            color=ft.Colors.WHITE,
            bgcolor="#1E3A8A",
            on_click=self._add_entry,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(18, 15, 18, 15),
            ),
        )

        # ── Initial Cash Balance input controls ──
        initial_cash_val = self.db.get_setting("initial_cash_balance", "0.00")
        self.initial_cash_field = ft.TextField(
            label="النقدية الافتتاحية (EGP) / Initial Cash",
            width=220,
            value=initial_cash_val,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._save_initial_cash,
            **input_style,
        )
        self.btn_save_initial = ft.ElevatedButton(
            "حفظ / Save",
            icon=ft.Icons.SAVE_ROUNDED,
            color=ft.Colors.WHITE,
            bgcolor="#1E3A8A",
            on_click=self._save_initial_cash,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(18, 15, 18, 15),
            ),
        )

        # ── KPI cards ──────────────────────────────────────────────────
        self.initial_cash_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400)
        self.cash_in_text  = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.cash_out_text = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.balance_text  = ft.Text("0.00 EGP", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)

        self.profit_wallet_text  = ft.Text("0.00 EGP", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300)
        self.profit_cash_text    = ft.Text("0.00 EGP", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
        self.profit_unset_text   = ft.Text("0.00 EGP", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE54)

        # ── جدول السجل ────────────────────────────────────────────────
        self.ledger_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("التاريخ / Date",      weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("النوع / Type",        weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("المبلغ / Amount",     weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("الوصف / Description", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT)),
                ft.DataColumn(ft.Text("حذف",                 weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)),
            ],
            rows=[],
            expand=True,
            heading_row_color="#0B0F19",
            vertical_lines=ft.BorderSide(1, ft.Colors.WHITE10),
            horizontal_lines=ft.BorderSide(1, ft.Colors.WHITE10),
        )

        # ── pagination ────────────────────────────────────────────────
        self.prev_btn  = ft.IconButton(ft.Icons.NAVIGATE_BEFORE_ROUNDED, on_click=self._prev_page, disabled=True)
        self.next_btn  = ft.IconButton(ft.Icons.NAVIGATE_NEXT_ROUNDED,   on_click=self._next_page, disabled=True)
        self.page_info = ft.Text("Page 1 of 1", color=ft.Colors.WHITE70)

        # ── Layout ────────────────────────────────────────────────────
        self.content = ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=ft.Colors.AMBER_400, size=32),
                        ft.Text("إدارة النقدية / Cash Management", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=10, color=ft.Colors.WHITE24),

                # ── KPI Row ──
                ft.Row(
                    controls=[
                        self._kpi("النقدية الافتتاحية / Initial", self.initial_cash_text, ft.Icons.ACCOUNT_BALANCE_ROUNDED, ["#1E3A8A","#1E1B4B"], ft.Colors.BLUE_400),
                        self._kpi("نقدية داخلة / Cash In",    self.cash_in_text,  ft.Icons.ARROW_DOWNWARD_ROUNDED,  ["#064E3B","#022C22"], ft.Colors.GREEN_400),
                        self._kpi("نقدية خارجة / Cash Out",   self.cash_out_text, ft.Icons.ARROW_UPWARD_ROUNDED,    ["#7F1D1D","#450A0A"], ft.Colors.RED_400),
                        self._kpi("الرصيد النقدي / Balance",  self.balance_text,  ft.Icons.WALLET_ROUNDED,          ["#78350F","#451A03"], ft.Colors.AMBER_300, width=220),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    wrap=True,
                    spacing=15,
                ),
                ft.Divider(height=10, color=ft.Colors.WHITE24),

                # ── Profit Summary ──
                ft.Text("تفصيل الأرباح / Profit Breakdown", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row(
                    controls=[
                        self._kpi("أرباح في المحفظة", self.profit_wallet_text, ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, ["#14532D","#0A1A0A"], ft.Colors.GREEN_300),
                        self._kpi("أرباح نقدياً",     self.profit_cash_text,   ft.Icons.MONETIZATION_ON_ROUNDED,          ["#78350F","#291200"], ft.Colors.AMBER_300),
                        self._kpi("غير محددة",         self.profit_unset_text,  ft.Icons.HELP_OUTLINE_ROUNDED,             ["#1E293B","#0F172A"], ft.Colors.WHITE54),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    wrap=True,
                    spacing=15,
                ),
                ft.Divider(height=15, color=ft.Colors.WHITE24),

                # ── Initial Cash Balance Form ──
                ft.Text("النقدية الافتتاحية / Initial Cash Balance", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Container(
                    content=ft.Row(
                        controls=[self.initial_cash_field, self.btn_save_initial],
                        wrap=True,
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor="#0B0F19",
                    padding=15,
                    border_radius=15,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    margin=ft.Margin(0, 0, 0, 10),
                ),

                # ── Add Entry Form ──
                ft.Text("إضافة حركة نقدية / Add Cash Entry", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Container(
                    content=ft.Row(
                        controls=[self.type_dropdown, self.amount_field, self.desc_field, self.btn_add],
                        wrap=True,
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor="#0B0F19",
                    padding=15,
                    border_radius=15,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    margin=ft.Margin(0, 0, 0, 10),
                ),

                # ── Ledger Table ──
                ft.Text("سجل الحركات / Transaction Log", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Container(
                    content=ft.Column([self.ledger_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=15,
                    bgcolor=ft.Colors.BLACK26,
                    padding=10,
                ),

                # Pagination
                ft.Row(
                    controls=[self.prev_btn, self.page_info, self.next_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            scroll=ft.ScrollMode.ADAPTIVE,
        )

    # ────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────

    def _kpi(self, title, text_ctrl, icon, grad, accent, width=200):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, color=accent, size=18),
                                bgcolor=ft.Colors.with_opacity(0.12, accent),
                                padding=8, border_radius=20,
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, accent)),
                            ),
                            ft.Text(title, color=ft.Colors.WHITE, size=11,
                                    weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=8, color=ft.Colors.WHITE10),
                    ft.Container(content=text_ctrl, alignment=ft.alignment.Alignment.CENTER, expand=True),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            width=width, height=110,
            gradient=ft.LinearGradient(colors=grad,
                                        begin=ft.alignment.Alignment.TOP_LEFT,
                                        end=ft.alignment.Alignment.BOTTOM_RIGHT),
            border_radius=16, padding=12,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.18, accent)),
            shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
        )

    # ────────────────────────────────────────────────────────────────────
    # Events
    # ────────────────────────────────────────────────────────────────────

    def _add_entry(self, e=None):
        entry_type = self.type_dropdown.value
        amount_str = (self.amount_field.value or "").strip()
        description = (self.desc_field.value or "").strip()

        if not amount_str:
            self._snack("⚠️ الرجاء إدخال المبلغ!", ft.Colors.ORANGE_700)
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            self._snack("⚠️ الرجاء إدخال مبلغ صحيح موجب!", ft.Colors.RED_700)
            return

        ok = self.db.add_cash_entry(entry_type, amount, description)
        if ok:
            self.amount_field.value = ""
            self.desc_field.value = ""
            label = ENTRY_TYPES[entry_type]["label"]
            self._snack(f"✅ تمت إضافة: {label} — {amount:,.2f} EGP", ft.Colors.GREEN_700)
            self.update_data()
        else:
            self._snack("❌ فشل في الإضافة، حاول مرة أخرى.", ft.Colors.RED_700)

    def _save_initial_cash(self, e=None):
        val_str = (self.initial_cash_field.value or "").strip()
        if not val_str:
            self._snack("⚠️ الرجاء إدخال قيمة النقدية الافتتاحية!", ft.Colors.ORANGE_700)
            return
        try:
            val = float(val_str)
            if val < 0:
                raise ValueError("Must be non-negative")
        except ValueError:
            self._snack("⚠️ الرجاء إدخال رقم صحيح غير سالب!", ft.Colors.RED_700)
            return

        ok = self.db.set_setting("initial_cash_balance", f"{val:.2f}")
        if ok:
            self._snack("✅ تم حفظ النقدية الافتتاحية بنجاح", ft.Colors.GREEN_700)
            self.update_data()
        else:
            self._snack("❌ فشل في الحفظ، حاول مرة أخرى.", ft.Colors.RED_700)

    def _delete_entry(self, entry_id: int):
        ok = self.db.delete_cash_entry(entry_id)
        if ok:
            self._snack("🗑️ تم الحذف بنجاح", ft.Colors.GREEN_800)
            self.update_data()
        else:
            self._snack("❌ فشل في الحذف", ft.Colors.RED_700)

    def _prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_ledger()

    def _next_page(self, e):
        self.current_page += 1
        self._refresh_ledger()

    def _snack(self, msg: str, color=ft.Colors.GREEN_700):
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, size=14, weight=ft.FontWeight.BOLD),
            bgcolor=color,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()

    # ────────────────────────────────────────────────────────────────────
    # Data Update
    # ────────────────────────────────────────────────────────────────────

    def update_data(self):
        """تحديث جميع البيانات"""
        self._refresh_kpi()
        self._refresh_profit()
        self._refresh_ledger()
        self.flet_page.update()

    def _refresh_kpi(self):
        cs = self.db.get_cash_summary()
        self.initial_cash_text.value = f"{cs['initial_cash']:,.2f} EGP"
        self.cash_in_text.value  = f"+{cs['total_in']:,.2f} EGP"
        self.cash_out_text.value = f"-{cs['total_out']:,.2f} EGP"
        bal = cs["balance"]
        self.balance_text.value = f"{bal:,.2f} EGP"
        self.balance_text.color = ft.Colors.AMBER_300 if bal >= 0 else ft.Colors.RED_400

    def _refresh_profit(self):
        ps = self.db.get_profit_summary()
        self.profit_wallet_text.value = f"{ps['in_wallet']:,.2f} EGP"
        self.profit_cash_text.value   = f"{ps['cash']:,.2f} EGP"
        self.profit_unset_text.value  = f"{ps['unset']:,.2f} EGP"

    def _refresh_ledger(self):
        total = self.db.get_cash_ledger_count()
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = total_pages

        offset = (self.current_page - 1) * self.page_size
        entries = self.db.get_cash_ledger(limit=self.page_size, offset=offset)

        self.prev_btn.disabled = self.current_page == 1
        self.next_btn.disabled = self.current_page >= total_pages
        self.page_info.value = f"Page {self.current_page} of {total_pages} ({total} entries)"

        self.ledger_table.rows.clear()
        for idx, e in enumerate(entries):
            e_type = e.get("type", "")
            style = ENTRY_TYPES.get(e_type, {"color": "#64748B", "label": e_type})
            amount = e.get("amount", 0.0)
            is_out = e_type in ("CASH_OUT", "EXPENSE")
            amount_sign = f"-{amount:,.2f}" if is_out else f"+{amount:,.2f}"
            amount_color = ft.Colors.RED_400 if is_out else ft.Colors.GREEN_400

            row_color = ft.Colors.with_opacity(0.04, ft.Colors.WHITE) if idx % 2 != 0 else ft.Colors.TRANSPARENT

            try:
                dt = datetime.fromisoformat(e["created_at"]).strftime("%Y-%m-%d %H:%M")
            except Exception:
                dt = e.get("created_at", "")

            entry_id = e.get("id")
            self.ledger_table.rows.append(
                ft.DataRow(
                    color=row_color,
                    cells=[
                        ft.DataCell(ft.Text(dt, color=ft.Colors.WHITE70, size=12)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(AR_LABELS.get(e_type, e_type), size=11,
                                                color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                bgcolor=ft.Colors.with_opacity(0.18, style["color"]),
                                border=ft.Border.all(1, ft.Colors.with_opacity(0.3, style["color"])),
                                padding=ft.Padding(10, 4, 10, 4),
                                border_radius=10,
                            )
                        ),
                        ft.DataCell(ft.Text(f"{amount_sign} EGP", color=amount_color,
                                            weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(e.get("description") or "—", color=ft.Colors.WHITE70)),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                icon_color=ft.Colors.RED_400,
                                icon_size=18,
                                tooltip="حذف / Delete",
                                on_click=lambda ev, eid=entry_id: self._delete_entry(eid),
                            )
                        ),
                    ],
                )
            )
