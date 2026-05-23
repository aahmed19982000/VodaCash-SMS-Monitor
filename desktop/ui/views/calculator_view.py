# desktop/ui/views/calculator_view.py
import flet as ft
from desktop.db.database import DesktopDatabase
from shared.models import Transaction, TransactionType

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

class CalculatorView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.expand = True
        self.padding = 20

        # Input Controls
        self.wallet_dropdown = ft.Dropdown(
            label="Wallet / المحفظة",
            options=[
                ft.dropdown.Option("vodafone_cash", "Vodafone Cash / فودافون كاش"),
                ft.dropdown.Option("orange_cash", "Orange Cash / أورنج كاش"),
                ft.dropdown.Option("etisalat_cash", "Etisalat Cash / اتصالات كاش"),
                ft.dropdown.Option("we_pay", "WE Pay / وي باي"),
                ft.dropdown.Option("instapay", "InstaPay / انستاباي"),
                ft.dropdown.Option("bank", "Bank Account / حساب بنكي"),
            ],
            value="vodafone_cash",
            on_select=self.calculate_fees,
            border_radius=12,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.type_dropdown = ft.Dropdown(
            label="Transaction Type / نوع المعاملة",
            options=[
                ft.dropdown.Option("SENT", "Deposit to Customer / إيداع للعميل"),
                ft.dropdown.Option("RECEIVED", "Withdrawal from Customer / سحب من العميل"),
            ],
            value="RECEIVED",
            on_select=self.calculate_fees,
            border_radius=12,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.amount_field = ft.TextField(
            label="Amount (EGP) / المبلغ (ج.م)",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.calculate_fees,
            on_submit=self.calculate_fees,
            autofocus=True,
            border_radius=12,
            bgcolor="#0B0F19",
            border_color=ft.Colors.WHITE24,
            focused_border_color=ft.Colors.BLUE_ACCENT,
            filled=True
        )

        self.btn_calculate = ft.ElevatedButton(
            "Calculate / احسب",
            icon=ft.Icons.CALCULATE_ROUNDED,
            color=ft.Colors.WHITE,
            bgcolor="#1E3A8A",
            on_click=self.calculate_fees,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(20, 18, 20, 18),
            )
        )

        self.btn_clear = ft.OutlinedButton(
            "Clear / مسح",
            icon=ft.Icons.CLEAR_ALL_ROUNDED,
            on_click=self.clear_calculator,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(20, 18, 20, 18),
            )
        )

        # Result Placeholder
        self.result_placeholder = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.CALCULATE_OUTLINED, size=72, color=ft.Colors.WHITE30),
                    ft.Text(
                        "Enter transaction details to calculate profit / fees\nأدخل تفاصيل المعاملة لحساب الأرباح والرسوم",
                        size=15,
                        color=ft.Colors.WHITE30,
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.Alignment.CENTER
        )

        # Detailed Result Panel
        self.wallet_info_icon = ft.Icon(ft.Icons.INFO_OUTLINED, color=ft.Colors.BLUE_400, size=20)
        self.wallet_info_text = ft.Text("", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE)
        
        self.wallet_info_container = ft.Container(
            content=ft.Row(
                controls=[
                    self.wallet_info_icon,
                    self.wallet_info_text
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor="#0F172A",
            padding=14,
            border_radius=12,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.BLUE_400))
        )
        
        self.fee_text = ft.Text("0.00 EGP", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)
        
        self.fee_summary_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Calculated Profit (Fee) / قيمة الربح (الرسوم) المحسوبة", size=13, color=ft.Colors.WHITE60, weight=ft.FontWeight.W_500),
                    self.fee_text
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.alignment.Alignment.CENTER,
            gradient=ft.LinearGradient(
                colors=["#241505", "#0E0701"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            padding=18,
            border_radius=16,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.AMBER_400))
        )
        
        self.option_a_net = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.option_a_total = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        self.option_b_net = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        self.option_b_total = ft.Text("0.00 EGP", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

        self.option_a_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Option A: Deducted from Amount\nالخيار أ: الخصم من المبلغ المرسل", size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE),
                    ft.Divider(height=12, color=ft.Colors.WHITE10),
                    ft.Text("Recipient Receives / يصل للمستلم", size=11, color=ft.Colors.WHITE60),
                    self.option_a_net,
                    ft.Container(height=5),
                    ft.Text("Total Deducted / الإجمالي المخصوم", size=11, color=ft.Colors.WHITE60),
                    self.option_a_total,
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            gradient=ft.LinearGradient(
                colors=["#1E293B", "#0F172A"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=20,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
            expand=True
        )

        self.option_b_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Option B: Added to Amount\nالخيار ب: الإضافة فوق المبلغ المرسل", size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color=ft.Colors.WHITE),
                    ft.Divider(height=12, color=ft.Colors.WHITE10),
                    ft.Text("Recipient Receives / يصل للمستلم", size=11, color=ft.Colors.WHITE60),
                    self.option_b_net,
                    ft.Container(height=5),
                    ft.Text("Total Paid / إجمالي المطلوب دفعه", size=11, color=ft.Colors.WHITE60),
                    self.option_b_total,
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            gradient=ft.LinearGradient(
                colors=["#0A2E20", "#081C15"],
                begin=ft.alignment.Alignment.TOP_LEFT,
                end=ft.alignment.Alignment.BOTTOM_RIGHT
            ),
            border_radius=16,
            padding=20,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.GREEN_400)),
            expand=True
        )

        self.result_container = ft.Container(
            content=ft.Column(
                controls=[
                    self.wallet_info_container,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    self.fee_summary_container,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        controls=[
                            self.option_a_container,
                            self.option_b_container
                        ],
                        spacing=15,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ],
                spacing=10
            ),
            visible=False,
            expand=True
        )

        self.right_column = ft.Container(
            content=ft.Stack([self.result_placeholder, self.result_container]),
            expand=True,
            bgcolor="#0B0F19",
            border_radius=15,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            padding=20
        )

        # Layout Main UI
        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CALCULATE_ROUNDED, color=ft.Colors.BLUE_ACCENT, size=32),
                        ft.Text("Profit & Fees Calculator / حاسبة الأرباح والرسوم للمعاملات", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Divider(height=10, color=ft.Colors.WHITE24),
                ft.Row(
                    controls=[
                        # Left side input form
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    self.wallet_dropdown,
                                    self.type_dropdown,
                                    self.amount_field,
                                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                    ft.Row(
                                        controls=[
                                            self.btn_calculate,
                                            self.btn_clear
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                    )
                                ],
                                spacing=15
                            ),
                            width=380,
                            bgcolor="#0B0F19",
                            border_radius=15,
                            border=ft.Border.all(1, ft.Colors.WHITE10),
                            padding=20,
                            alignment=ft.alignment.Alignment.TOP_CENTER
                        ),
                        
                        # Right side details panel
                        self.right_column
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    spacing=20
                )
            ],
            expand=True
        )

    def calculate_fees(self, e=None):
        try:
            amt_str = self.amount_field.value.strip()
            if not amt_str:
                self.show_placeholder()
                return
            
            amount = float(amt_str)
            if amount <= 0:
                self.show_placeholder()
                return
        except ValueError:
            self.show_placeholder()
            return

        w_id = self.wallet_dropdown.value
        tx_type = self.type_dropdown.value
        
        # Get rules from settings
        dep_fee_str = self.db.get_setting(f"fee_deposit_{w_id}", "0.0")
        wth_fee_str = self.db.get_setting(f"fee_withdraw_{w_id}", "0.0")
        wth_min_str = self.db.get_setting(f"fee_withdraw_min_{w_id}", "0.0")
        
        try:
            dep_fee_pct = float(dep_fee_str)
            wth_fee_pct = float(wth_fee_str)
            wth_min = float(wth_min_str)
        except ValueError:
            dep_fee_pct = 0.0
            wth_fee_pct = 0.0
            wth_min = 0.0

        # Style layout colors according to wallet brand color
        style = WALLET_STYLING.get(w_id, WALLET_STYLING["unspecified"])
        accent_color = style["accent_color"]
        
        # Update wallet summary container colors to match
        self.wallet_info_icon.color = accent_color
        self.wallet_info_container.border = ft.Border.all(1, ft.Colors.with_opacity(0.35, accent_color))
        self.wallet_info_container.bgcolor = ft.Colors.with_opacity(0.06, accent_color)
        
        # Rules text summary
        if tx_type == "SENT":
            self.wallet_info_text.value = f"{style['name']} — Deposit Profit Rate: {dep_fee_pct}% (Min {wth_min} EGP) | أرباح الإيداع: {dep_fee_pct}% (حد أدنى {wth_min} ج.م)"
            # Dynamic fee calculation for Option A (based on base amount)
            dummy_tx = Transaction(
                type=TransactionType.SENT,
                amount=amount,
                wallet_id=w_id
            )
            fee = self.db.calculate_fee(dummy_tx)
            
            # Option A: Deducted from amount (Amount = Total Paid)
            opt_a_total = amount
            opt_a_net = max(0.0, amount - fee)
            
            # Option B: Add fee to amount (Target Net = Amount)
            if dep_fee_pct < 100.0:
                opt_b_total = amount / (1.0 - (dep_fee_pct / 100.0))
                fee_b = opt_b_total - amount
            else:
                opt_b_total = amount
                fee_b = 0.0

            if fee_b < wth_min:
                fee_b = wth_min
                opt_b_total = amount + wth_min
                
            opt_b_net = amount
            
        else: # RECEIVED
            self.wallet_info_text.value = f"{style['name']} — Withdraw Profit Rate: {wth_fee_pct}% (Min {wth_min} EGP) | أرباح السحب: {wth_fee_pct}% (حد أدنى {wth_min} ج.م)"
            # Dynamic fee calculation for Option A (based on base amount)
            dummy_tx = Transaction(
                type=TransactionType.RECEIVED,
                amount=amount,
                wallet_id=w_id
            )
            fee = self.db.calculate_fee(dummy_tx)
            
            # Option A: Deducted from amount (Total Deducted = Amount)
            opt_a_total = amount
            opt_a_net = max(0.0, amount - fee)
            
            # Option B: Added to amount
            opt_b_net = amount
            opt_b_total = amount + fee
            fee_b = fee

        self.fee_text.value = f"{fee:,.2f} EGP"
        
        self.option_a_net.value = f"{opt_a_net:,.2f} EGP"
        self.option_a_total.value = f"{opt_a_total:,.2f} EGP"
        
        self.option_b_net.value = f"{opt_b_net:,.2f} EGP"
        self.option_b_total.value = f"{opt_b_total:,.2f} EGP"
        
        # Show Results Panel
        self.result_placeholder.visible = False
        self.result_container.visible = True
        self.flet_page.update()

    def show_placeholder(self):
        self.result_placeholder.visible = True
        self.result_container.visible = False
        self.flet_page.update()

    def clear_calculator(self, e=None):
        self.amount_field.value = ""
        self.wallet_dropdown.value = "vodafone_cash"
        self.type_dropdown.value = "SENT"
        self.show_placeholder()

    def update_data(self):
        # Refresh calculations in case settings changed
        self.calculate_fees()
