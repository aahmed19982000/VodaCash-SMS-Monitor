# desktop/ui/views/transfer_view.py
import flet as ft
import asyncio
from desktop.db.database import DesktopDatabase
from shared.protocol import make_initiate_transfer

class TransferView(ft.Container):
    def __init__(self, page: ft.Page, db: DesktopDatabase, server=None):
        super().__init__()
        self.flet_page = page
        self.db = db
        self.server = server
        self.selected_wallet = None

        self.expand = True
        self.padding = 20
        self.bgcolor = ft.Colors.TRANSPARENT

        # Wallet Options styling
        self.wallets = {
            "vodafone_cash": {
                "name": "Vodafone Cash",
                "name_ar": "فودافون كاش",
                "color": "#EF4444",
                "gradient": ["#E60000", "#500000"],
                "icon": ft.Icons.PHONE_ANDROID,
            },
            "orange_cash": {
                "name": "Orange Cash",
                "name_ar": "أورنج كاش",
                "color": "#F97316",
                "gradient": ["#FF6600", "#602000"],
                "icon": ft.Icons.MONEY_ROUNDED,
            },
            "etisalat_cash": {
                "name": "Etisalat Cash",
                "name_ar": "اتصالات كاش",
                "color": "#22C55E",
                "gradient": ["#78B833", "#153005"],
                "icon": ft.Icons.PHONELINK_RING,
            },
            "we_pay": {
                "name": "WE Pay",
                "name_ar": "وي باي",
                "color": "#A855F7",
                "gradient": ["#8C3893", "#300538"],
                "icon": ft.Icons.PAYMENT,
            }
        }

        self.setup_ui()

    def setup_ui(self):
        # 1. Header
        header = ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEND_ROUNDED, color=ft.Colors.BLUE_400, size=32),
                ft.Column(
                    controls=[
                        ft.Text("التحويل السريع للأموال / Quick Money Transfer", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Text("أرسل أمر التحويل تلقائياً للهاتف عبر الويب سوكيت دون الحاجة لإدخاله يدوياً", size=13, color=ft.Colors.WHITE54),
                    ],
                    spacing=2
                )
            ],
            spacing=15
        )

        # 2. Wallet selector grid
        self.wallet_cards = []
        for w_id, w_info in self.wallets.items():
            card = self.build_wallet_card(w_id, w_info)
            self.wallet_cards.append(card)

        wallet_selector_row = ft.Row(
            controls=self.wallet_cards,
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
        )

        # 3. Input Form
        self.recipient_field = ft.TextField(
            label="رقم الهاتف المستلم / Recipient Number",
            hint_text="01xxxxxxxxx",
            prefix_icon=ft.Icons.PHONE_ANDROID_ROUNDED,
            width=360,
            border_color="#1E293B",
            focused_border_color=ft.Colors.BLUE_400,
            color=ft.Colors.WHITE,
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
            keyboard_type=ft.KeyboardType.PHONE,
        )

        self.amount_field = ft.TextField(
            label="المبلغ المراد تحويله (EGP) / Amount",
            hint_text="0.00",
            prefix_icon=ft.Icons.MONETIZATION_ON_OUTLINED,
            width=360,
            border_color="#1E293B",
            focused_border_color=ft.Colors.BLUE_400,
            color=ft.Colors.WHITE,
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.pin_field = ft.TextField(
            label="الرقم السري للمحفظة / Wallet PIN (أمني ومحمي)",
            hint_text="•••••",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_ROUNDED,
            width=360,
            border_color="#1E293B",
            focused_border_color=ft.Colors.BLUE_400,
            color=ft.Colors.WHITE,
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # SIM Slot selection
        self.sim_slot_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(value="0", label="SIM 1 (الخط 1)", fill_color=ft.Colors.BLUE_400),
                    ft.Radio(value="1", label="SIM 2 (الخط 2)", fill_color=ft.Colors.BLUE_400),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=30,
            ),
            value="0"
        )
        
        sim_slot_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("شريحة الاتصال للتحويل / Outgoing SIM Slot", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                    self.sim_slot_radio
                ],
                spacing=5
            ),
            padding=5
        )

        # 4. Status banner
        self.status_banner = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.AMBER_400, size=20),
                    ft.Text("⚠️ الهاتف غير متصل بالخادم حالياً! لا يمكن إرسال أوامر تحويل.", color=ft.Colors.AMBER_400, size=13, weight=ft.FontWeight.W_500)
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10
            ),
            bgcolor="#251F10",
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.AMBER_400)),
            border_radius=10,
            padding=15,
            width=500,
            visible=True
        )

        # 5. Submit Button
        self.submit_btn = ft.Container(
            content=ft.ElevatedButton(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SEND_ROUNDED, color=ft.Colors.WHITE, size=18),
                        ft.Text("إرسال طلب التحويل للهاتف / Send Transfer", size=14, weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_800,
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
                on_click=self.on_submit_transfer,
            ),
            height=50,
            width=360,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.with_opacity(0.2, ft.Colors.BLUE_800))
        )

        form_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("بيانات عملية التحويل / Transfer Information", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                    ft.Divider(height=10, color=ft.Colors.WHITE10),
                    self.recipient_field,
                    self.amount_field,
                    self.pin_field,
                    ft.Container(height=5),
                    sim_slot_container,
                    ft.Container(height=5),
                    self.status_banner,
                    ft.Container(height=10),
                    self.submit_btn
                ],
                spacing=15,
            ),
            bgcolor="#0B0F19",
            padding=25,
            border_radius=18,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            alignment=ft.alignment.Alignment(-1, 0),
        )

        # Main Layout
        self.content = ft.Column(
            controls=[
                header,
                ft.Divider(height=15, color=ft.Colors.WHITE10),
                ft.Text("اختر محفظة التحويل / Choose Source Wallet", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE70),
                wallet_selector_row,
                ft.Container(height=10),
                form_section
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

    def build_wallet_card(self, wallet_id: str, info: dict) -> ft.Container:
        # Hover effect handling
        def on_hover(e):
            if self.selected_wallet == wallet_id:
                return
            if e.data == "true":
                e.control.border = ft.Border.all(2, info["color"])
                e.control.shadow = ft.BoxShadow(spread_radius=1, blur_radius=12, color=ft.Colors.with_opacity(0.25, info["color"]))
            else:
                e.control.border = ft.Border.all(1, ft.Colors.WHITE10)
                e.control.shadow = None
            e.control.update()

        def on_click(e):
            self.selected_wallet = wallet_id
            for card in self.wallet_cards:
                c_id = card.data
                c_info = self.wallets[c_id]
                if c_id == wallet_id:
                    card.border = ft.Border.all(3, c_info["color"])
                    card.shadow = ft.BoxShadow(spread_radius=2, blur_radius=16, color=ft.Colors.with_opacity(0.4, c_info["color"]))
                    card.bgcolor = "#151B2E"
                else:
                    card.border = ft.Border.all(1, ft.Colors.WHITE10)
                    card.shadow = None
                    card.bgcolor = "#0B0F19"
                card.update()

        card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(info["icon"], color=info["color"], size=28),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    ft.Container(height=10),
                    ft.Text(info["name"], size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(info["name_ar"], size=12, color=ft.Colors.WHITE54),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=5,
            ),
            width=165,
            height=125,
            padding=15,
            border_radius=15,
            bgcolor="#0B0F19",
            border=ft.Border.all(1, ft.Colors.WHITE10),
            on_hover=on_hover,
            on_click=on_click,
            data=wallet_id
        )
        return card

    def update_data(self):
        """Called automatically when switching views to update network connection status banner"""
        clients_count = self.server.connected_clients if self.server else 0
        print(f"[DEBUG] TransferView.update_data called. Connected clients: {clients_count}")
        if self.server and clients_count > 0:
            self.status_banner.visible = False
            self.submit_btn.content.disabled = False
        else:
            self.status_banner.visible = True
            self.submit_btn.content.disabled = True
        self.flet_page.update()

    def on_submit_transfer(self, e):
        print(f"[DEBUG] TransferView.on_submit_transfer clicked!")
        # 1. Validation
        if not self.selected_wallet:
            print("[DEBUG] Validation failed: selected_wallet is None")
            self.show_snack("الرجاء اختيار المحفظة أولاً! / Please choose a wallet!", True)
            return

        recipient = self.recipient_field.value.strip() if self.recipient_field.value else ""
        if not recipient or len(recipient) < 11:
            print(f"[DEBUG] Validation failed: recipient='{recipient}' (length: {len(recipient)})")
            self.show_snack("الرجاء إدخال رقم مستلم صحيح! / Please enter a valid recipient number!", True)
            return

        amount_str = self.amount_field.value.strip() if self.amount_field.value else ""
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            print(f"[DEBUG] Validation failed: amount_str='{amount_str}'")
            self.show_snack("الرجاء إدخال مبلغ صحيح! / Please enter a valid amount!", True)
            return

        pin = self.pin_field.value.strip() if self.pin_field.value else ""
        if not pin or len(pin) < 4:
            print(f"[DEBUG] Validation failed: pin length={len(pin)}")
            self.show_snack("الرجاء إدخال الرقم السري للمحفظة! / Please enter the wallet PIN!", True)
            return

        # Check connection status again
        clients_count = self.server.connected_clients if self.server else 0
        if not self.server or clients_count == 0:
            print(f"[DEBUG] Validation failed: server connection count: {clients_count}")
            self.show_snack("خطأ: الهاتف غير متصل! / Error: Mobile is not connected!", True)
            return

        sim_slot = int(self.sim_slot_radio.value) if self.sim_slot_radio.value else 0
        print(f"[DEBUG] Validation passed. Wallet: {self.selected_wallet}, Recipient: {recipient}, Amount: {amount}, SIM Slot: {sim_slot}")

        # 2. Build the websocket message
        msg_payload = make_initiate_transfer(self.selected_wallet, recipient, amount, pin, sim_slot=sim_slot)
        print(f"[DEBUG] Built message payload: {msg_payload[:100]}...")

        try:
            # Broadcast the transfer command to the phone over WebSocket thread-safely
            print(f"[DEBUG] Dispatching message thread-safely to WebSocket server...")
            self.server.broadcast_threadsafe(msg_payload)
            print(f"[DEBUG] Message successfully dispatched to broadcast threadsafe.")
            
            # Show success and clear PIN field for security
            self.pin_field.value = ""
            self.recipient_field.value = ""
            self.amount_field.value = ""
            self.show_snack(f"✅ تم إرسال طلب تحويل بمبلغ {amount:,.2f} EGP للموبايل! جاري التنفيذ...", False)
        except Exception as ex:
            print(f"[DEBUG] Error broadcasting message: {ex}")
            self.show_snack(f"❌ فشل إرسال الأمر: {ex}", True)

        self.flet_page.update()

    def show_snack(self, message: str, is_error: bool):
        self.flet_page.snack_bar = ft.SnackBar(
            content=ft.Text(message, size=14, weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_800,
        )
        self.flet_page.snack_bar.open = True
        self.flet_page.update()
