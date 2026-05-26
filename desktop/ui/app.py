# desktop/ui/app.py
import threading
import flet as ft
from desktop.db.database import DesktopDatabase
from desktop.ui.views.dashboard_view import DashboardView
from desktop.ui.views.transactions_view import TransactionsView
from desktop.ui.views.settings_view import SettingsView
from desktop.ui.views.phone_search_view import PhoneSearchView
from desktop.ui.views.top_contacts_view import TopContactsView
from desktop.ui.views.calculator_view import CalculatorView
from desktop.ui.views.cash_management_view import CashManagementView
from desktop.ui.views.transfer_view import TransferView
from desktop.ui.views.login_view import LoginView

class DesktopApp:
    def __init__(self, page: ft.Page, db: DesktopDatabase, server):
        self.page = page
        self.page.ui_app = self
        self.db = db
        self.server = server
        self.active_dialog = None
        self.dialog_lock = threading.Lock()
        self.dialog_queue = []

        # Status components
        self.status_icon = ft.Icon(ft.Icons.CIRCLE, size=10)
        self.status_text = ft.Text(weight=ft.FontWeight.BOLD, size=12)
        self.status_container = ft.Container(
            content=ft.Row(
                [
                    self.status_icon,
                    self.status_text,
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#1E293B",
            padding=ft.Padding(left=12, top=6, right=12, bottom=6),
            border_radius=20,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            margin=ft.Margin(left=0, top=0, right=15, bottom=0),
        )

        self.setup_page()

        # Initial status
        self.update_connection_status(self.server.connected_clients > 0)

        # Views
        self.dashboard_view = DashboardView(self.page, self.db, self.server)
        self.transactions_view = TransactionsView(self.page, self.db)
        self.top_contacts_view = TopContactsView(self.page, self.db)
        self.phone_search_view = PhoneSearchView(self.page, self.db)
        self.calculator_view = CalculatorView(self.page, self.db)
        self.transfer_view = TransferView(self.page, self.db, self.server)
        self.cash_management_view = CashManagementView(self.page, self.db)
        self.settings_view = SettingsView(
            self.page,
            db=self.db,
            server=self.server,
            on_clear_success=self.refresh_all_views
        )

        # Navigation
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=90,
            min_extended_width=200,
            group_alignment=-0.9,
            bgcolor=ft.Colors.TRANSPARENT,
            indicator_color=ft.Colors.with_opacity(0.12, "#1E8F8B"),
            selected_label_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, color="#1E8F8B", size=12),
            unselected_label_text_style=ft.TextStyle(color=ft.Colors.WHITE54, size=11),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD_ROUNDED,
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIST_ALT_OUTLINED,
                    selected_icon=ft.Icons.LIST_ALT_ROUNDED,
                    label="Transactions",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE_ROUNDED,
                    label="Top Contacts",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PERSON_SEARCH_OUTLINED,
                    selected_icon=ft.Icons.PERSON_SEARCH_ROUNDED,
                    label="Phone Search",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALCULATE_OUTLINED,
                    selected_icon=ft.Icons.CALCULATE_ROUNDED,
                    label="Calculator",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEND_OUTLINED,
                    selected_icon=ft.Icons.SEND_ROUNDED,
                    label="Transfer",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                    label="Cash",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS_ROUNDED,
                    label="Connection",
                ),
            ],
            on_change=self.on_nav_change,
        )

        # Container for the active view
        self.view_container = ft.Container(
            content=self.dashboard_view,
            expand=True,
            padding=15
        )

        # Banner container for notifications/warnings
        self.banner_container = ft.Container(visible=False)

        # Right column containing banner + view
        self.right_column = ft.Column(
            [
                self.banner_container,
                self.view_container
            ],
            expand=True,
            spacing=0
        )

        # Layout
        self.main_layout = ft.Row(
            [
                self.rail,
                ft.VerticalDivider(width=1, color="#1E293B"),
                self.right_column,
            ],
            expand=True,
        )

        self.root_stack = ft.Stack(
            controls=[self.main_layout],
            expand=True,
        )

        self.page.add(self.root_stack)

        # Dynamic overlay helpers for child views
        self.page.show_dialog_overlay = self.show_dialog_overlay
        self.page.close_dialog_overlay = self.close_dialog_overlay

        # Callback for license logout/deactivation
        self.page.on_license_deactivated = self.show_login_screen

        # Check license key state
        self.check_license_on_startup()

    def check_license_on_startup(self):
        from datetime import datetime
        lic_key = self.db.get_setting("license_key", "")
        lic_expiry_str = self.db.get_setting("license_expiry", "")
        lic_status = self.db.get_setting("license_status", "EXPIRED")

        is_valid_local = False
        if lic_key and lic_status == "ACTIVE" and lic_expiry_str:
            try:
                expiry = datetime.fromisoformat(lic_expiry_str.replace("Z", "+00:00"))
                now_utc = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
                if expiry > now_utc:
                    is_valid_local = True
            except Exception:
                pass

        if not is_valid_local:
            self.show_login_screen()
        else:
            self.show_main_screen()
            self.check_expiry_warning()
            # Start background thread to verify key online
            import threading
            threading.Thread(target=self.verify_license_online_background, daemon=True).start()

    def verify_license_online_background(self):
        from desktop.utils.licensing import LicensingManager, get_mac_address
        lic_mgr = LicensingManager(db=self.db)
        lic_key = self.db.get_setting("license_key", "")
        mac = get_mac_address()
        
        res = lic_mgr.validate_license(lic_key, mac)
        
        def apply_status():
            if not res["success"]:
                self.db.set_setting("license_key", "")
                self.db.set_setting("license_expiry", "")
                self.db.set_setting("license_status", "EXPIRED")
                
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"⚠️ توقف التفعيل: {res['message']}", size=14, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.RED_700,
                    duration=6000
                )
                self.page.snack_bar.open = True
                self.show_login_screen()
            else:
                lic = res["license"]
                self.db.set_setting("license_expiry", lic["expires_at"])
                self.db.set_setting("license_status", "ACTIVE")
                self.check_expiry_warning()
                
        if self.page:
            self.page.run_thread(apply_status)

    def show_login_screen(self):
        from desktop.ui.views.login_view import LoginView
        self.login_view = LoginView(self.page, self.db, self.on_license_activated_success)
        self.root_stack.controls = [self.login_view]
        self.page.update()

    def show_main_screen(self):
        self.root_stack.controls = [self.main_layout]
        threading.Thread(target=self.refresh_views, daemon=True).start()
        self.page.update()

    def on_license_activated_success(self):
        self.show_main_screen()
        self.check_expiry_warning()

    def check_expiry_warning(self):
        from datetime import datetime
        lic_expiry_str = self.db.get_setting("license_expiry", "")
        if not lic_expiry_str:
            self.banner_container.visible = False
            self.page.update()
            return

        try:
            expiry = datetime.fromisoformat(lic_expiry_str.replace("Z", "+00:00"))
            now_utc = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
            
            self.banner_container.visible = False
            self.banner_container.content = None

            if now_utc >= expiry:
                self.banner_container.visible = True
                self.banner_container.content = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.YELLOW_300, size=20),
                            ft.Text("⚠️ انتهى اشتراكك. تم إيقاف استقبال العمليات الجديدة وتجميد الخدمة. يمكنك تصفح السجل التاريخي فقط.", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    bgcolor=ft.Colors.RED_900,
                    padding=ft.Padding(10, 8, 10, 8),
                    alignment=ft.alignment.Alignment.CENTER
                )
            else:
                days_left = (expiry - now_utc).days
                if days_left <= 5:
                    self.banner_container.visible = True
                    self.banner_container.content = ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.WHITE, size=18),
                                ft.Text(f"⚠️ ينتهي اشتراكك خلال {days_left + 1} أيام. يرجى تجديد الاشتراك لتفادي توقف الخدمة.", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10
                        ),
                        bgcolor=ft.Colors.AMBER_800,
                        padding=ft.Padding(10, 8, 10, 8),
                        alignment=ft.alignment.Alignment.CENTER
                    )
        except Exception as e:
            print(f"Error checking expiry warning: {e}")

        
        self.page.update()

    def setup_page(self):

        self.page.title = "دفتر كاش - Daftar Cash"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#080C14"
        self.page.theme = ft.Theme(
            color_scheme_seed="#1E8F8B",
            font_family="Segoe UI, Tahoma, Geneva, Verdana, sans-serif"
        )
        self.page.padding = 0
        self.page.window.width = 1250
        self.page.window.height = 820
        self.page.window.min_width = 850
        self.page.window.min_height = 620

        # Add AppBar
        self.page.appbar = ft.AppBar(
            leading=ft.Container(content=ft.Image(src="/logo.png", fit="contain"), padding=ft.Padding(left=8, top=5, right=0, bottom=5)),
            leading_width=50,
            title=ft.Text("دفتر كاش - Daftar Cash", weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.WHITE),
            center_title=False,
            bgcolor="#0B0F19",
            elevation=0,
            actions=[self.status_container]
        )

    def on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.view_container.content = self.dashboard_view
        elif idx == 1:
            self.view_container.content = self.transactions_view
        elif idx == 2:
            self.view_container.content = self.top_contacts_view
        elif idx == 3:
            self.view_container.content = self.phone_search_view
        elif idx == 4:
            self.view_container.content = self.calculator_view
        elif idx == 5:
            self.view_container.content = self.transfer_view
        elif idx == 6:
            self.view_container.content = self.cash_management_view
        elif idx == 7:
            self.view_container.content = self.settings_view
        self.page.update()
        
        # تشغيل جلب البيانات في الخلفية لتفادي تعليق الواجهة
        threading.Thread(target=self.refresh_views, daemon=True).start()

    def refresh_views(self):
        """تحديث الواجهة الحالية بالبيانات الجديدة"""
        if self.view_container.content == self.dashboard_view:
            self.dashboard_view.update_data()
        elif self.view_container.content == self.transactions_view:
            self.transactions_view.update_data()
        elif self.view_container.content == self.top_contacts_view:
            self.top_contacts_view.update_data()
        elif self.view_container.content == self.phone_search_view:
            self.phone_search_view.update_data()
        elif self.view_container.content == self.calculator_view:
            self.calculator_view.update_data()
        elif self.view_container.content == self.transfer_view:
            self.transfer_view.update_data()
        elif self.view_container.content == self.cash_management_view:
            self.cash_management_view.update_data()
        elif self.view_container.content == self.settings_view:
            self.settings_view.update_data()

    def refresh_all_views(self):
        """تحديث كافة الصفحات بالبيانات الجديدة"""
        try:
            self.dashboard_view.update_data()
            self.transactions_view.update_data()
            self.top_contacts_view.update_data()
            self.phone_search_view.update_data()
            self.calculator_view.update_data()
            self.transfer_view.update_data()
            self.cash_management_view.update_data()
        except Exception as e:
            print(f"Error refreshing all views: {e}")

    def update_connection_status(self, is_connected: bool):
        if is_connected:
            self.status_icon.color = ft.Colors.GREEN_400
            self.status_text.value = "الموبايل: متصل"
            self.status_text.color = ft.Colors.GREEN_400
            self.status_container.border = ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.GREEN_400))
            self.status_container.bgcolor = "#0A241A"
        else:
            self.status_icon.color = ft.Colors.RED_400
            self.status_text.value = "الموبايل: غير متصل"
            self.status_text.color = ft.Colors.RED_400
            self.status_container.border = ft.Border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.RED_400))
            self.status_container.bgcolor = "#250F12"
        self.page.update()

        # Update transfer view UI state dynamically
        if hasattr(self, "transfer_view") and self.transfer_view:
            try:
                self.transfer_view.update_data()
            except Exception as e:
                print(f"Error updating transfer view on connection change: {e}")

    def show_dialog_overlay(self, dlg):
        """عرض نافذة منبثقة باستخدام Stack الرئيسي بدلاً من overlay الخاص بـ page لتفادي تجميد الأزرار"""
        try:
            with self.dialog_lock:
                if dlg not in self.root_stack.controls:
                    self.root_stack.controls.append(dlg)
            self.page.update()
        except Exception as e:
            print(f"Error showing dialog overlay: {e}")

    def close_dialog_overlay(self, dlg):
        """إغلاق نافذة منبثقة معينة من Stack الرئيسي"""
        try:
            with self.dialog_lock:
                if dlg in self.root_stack.controls:
                    self.root_stack.controls.remove(dlg)
            self.page.update()
        except Exception as e:
            print(f"Error closing dialog overlay: {e}")

    def _close_new_tx_dialog(self, dlg=None):
        try:
            with self.dialog_lock:
                if dlg and dlg in self.root_stack.controls:
                    try:
                        self.root_stack.controls.remove(dlg)
                    except Exception:
                        pass
                
                # Clean up any other controls in root_stack that have data == "new_transaction_dialog"
                to_remove = []
                for ctrl in self.root_stack.controls:
                    if getattr(ctrl, "data", None) == "new_transaction_dialog":
                        to_remove.append(ctrl)
                
                for ctrl in to_remove:
                    try:
                        self.root_stack.controls.remove(ctrl)
                    except Exception:
                        pass
                
                self.active_dialog = None

                # تحقق مما إذا كان هناك عمليات أخرى في طابور النوافذ لعرضها متتالية
                if hasattr(self, "dialog_queue") and self.dialog_queue:
                    next_tx = self.dialog_queue.pop(0)
                    next_fee = self.db.calculate_fee(next_tx)
                    if next_fee > 0.0:
                        self._show_new_tx_dialog(next_tx, next_fee)
            self.page.update()
        except Exception as e:
            print(f"Error closing dialog: {e}")

    def _set_new_tx_profit_status(self, tx, fee: float, status: str, dlg):
        try:
            # تحديث حالة الأرباح في قاعدة البيانات
            ok = self.db.mark_profit_status(tx.transaction_id, tx.raw_sms, status)
            if ok and status == "CASH":
                tx_type_str = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
                tx_amount_val = tx.amount if tx.amount is not None else 0.0
                desc = f"ربح من {tx_type_str} — {tx.wallet_id or ''} — {tx_amount_val:,.2f} EGP"
                self.db.add_cash_entry("PROFIT_IN", fee, desc, source_tx_id=str(tx.transaction_id or ""))
            
            self._close_new_tx_dialog(dlg)
            
            # إظهار رسالة تأكيد للمستخدم
            status_labels = {"IN_WALLET": "💳 في المحفظة", "CASH": "💵 نقداً", "NONE": "✖ لا ربح"}
            if ok:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ تم حفظ حالة الربح: {status_labels.get(status, status)}", size=14, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.GREEN_800,
                )
            else:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("❌ حدث خطأ أثناء حفظ الحالة.", size=14),
                    bgcolor=ft.Colors.RED_700,
                )
            self.page.snack_bar.open = True
            self.refresh_all_views()
            self.page.update()
        except Exception as e:
            print(f"Error setting profit status: {e}")
            self._close_new_tx_dialog(dlg)

    def handle_new_transaction(self, tx, is_live=False):
        """التعامل مع عملية جديدة واردة وعرض نافذة منبثقة للأرباح إن وجدت"""
        # تحديث كافة الشاشات مباشرة لرؤية العملية فوراً
        self.refresh_all_views()
        self.page.update()

        # التحقق من أن العملية تمت معالجتها بالفعل لتجنب تراكم النوافذ المنبثقة
        try:
            # إذا كانت العملية موجودة بالفعل وحالة أرباحها ليست معلقة (UNSET)
            existing_status = self.db.get_transaction_profit_status(tx.transaction_id)
            if existing_status != "UNSET":
                print(f"Skipping profit popup for already processed transaction {tx.transaction_id} (status: {existing_status})")
                return
        except Exception as ex:
            print(f"Error checking transaction status: {ex}")

        # التحقق من الرسوم أولاً لتفادي غلق نافذة مفتوحة إذا كانت العملية الجديدة لا تحمل أرباحاً
        fee = self.db.calculate_fee(tx)
        if fee <= 0.0:
            return

        with self.dialog_lock:
            if self.active_dialog is not None:
                # إذا كانت هناك نافذة مفتوحة بالفعل، نقوم بإضافة العملية إلى الطابور لعرضها لاحقاً
                if not hasattr(self, "dialog_queue"):
                    self.dialog_queue = []
                self.dialog_queue.append(tx)
                print(f"Enqueued transaction {tx.transaction_id} to dialog queue. Queue length: {len(self.dialog_queue)}")
                return

            self._show_new_tx_dialog(tx, fee)

    def handle_new_unclassified(self, payload):
        """التعامل مع رسالة جديدة غير مصنفة وتنبيه المستخدم وتحديث الواجهة"""
        try:
            self.refresh_all_views()
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("📬 تم استقبال رسالة غير مصنفة جديدة. يرجى مراجعتها وتصنيفها يدوياً.", size=14, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.BLUE_900,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            print(f"Error handling new unclassified SMS: {e}")

    def _show_new_tx_dialog(self, tx, fee):
        amount_val = tx.amount if tx.amount is not None else 0.0
        fee_val = fee if fee is not None else 0.0

        # تنظيف رقم الهاتف وإزالة مفتاح الدولة إذا وجد ليكون أوضح للمستخدم
        cp = tx.counterpart or ''
        if not cp or cp.strip() == '':
            # محاولة استخراج رقم الهاتف من نص الرسالة الخام إذا كان فارغاً
            import re
            phone_match = re.search(r'(?:\+?20|0020|20)?(01[0125]\d{8})\b', tx.raw_sms)
            if phone_match:
                cp = phone_match.group(1)
            else:
                phone_match_no_zero = re.search(r'(?:\+?20|0020|20)?(1[0125]\d{8})\b', tx.raw_sms)
                if phone_match_no_zero:
                    cp = "0" + phone_match_no_zero.group(1)
        
        cp = cp.strip() if cp else '—'
        if cp != '—':
            if cp.startswith("+2"):
                cp = cp[2:]
            elif cp.startswith("002"):
                cp = cp[3:]
            elif cp.startswith("201") and len(cp) == 12:
                cp = "0" + cp[2:]

        # تحديد العنوان بناءً على اتجاه المعاملة لتحديد الرقم المحول منه أو إليه
        tx_type_str = tx.type.value if hasattr(tx.type, "value") else str(tx.type)
        if tx_type_str == "RECEIVED":
            phone_label = "الرقم المحوّل منه / From"
        elif tx_type_str == "SENT":
            phone_label = "الرقم المحوّل إليه / To"
        elif tx_type_str == "TOPUP":
            phone_label = "رقم الشحن / Top-up To"
        elif tx_type_str == "BILL":
            phone_label = "الجهة المستلمة / Merchant"
        else:
            phone_label = "الرقم أو الجهة / Counterpart"

        custom_dlg = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.NOTIFICATION_IMPORTANT_ROUNDED, color=ft.Colors.AMBER_400, size=26),
                                ft.Text("معاملة جديدة بأرباح / New Profit Transaction", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"💰 قيمة الربح: {fee_val:,.2f} EGP", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                                ft.Divider(height=1, color=ft.Colors.WHITE10),
                                ft.Row([
                                    ft.Icon(ft.Icons.PHONE_ROUNDED, color=ft.Colors.BLUE_400, size=16),
                                    ft.Text(f"{phone_label}: {cp}", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                ], spacing=5),
                                ft.Row([
                                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=ft.Colors.GREEN_400, size=14),
                                    ft.Text(f"المحفظة: {tx.wallet_id or '—'}", size=12, color=ft.Colors.WHITE70),
                                    ft.VerticalDivider(width=10),
                                    ft.Icon(ft.Icons.MONETIZATION_ON_ROUNDED, color=ft.Colors.GREEN_400, size=14),
                                    ft.Text(f"المبلغ: {amount_val:,.2f} EGP", size=12, color=ft.Colors.WHITE70),
                                ], spacing=5),
                                ft.Row([
                                    ft.Icon(ft.Icons.SWAP_HORIZ_ROUNDED, color=ft.Colors.WHITE54, size=14),
                                    ft.Text(f"نوع العملية: {tx_type_str}", size=12, color=ft.Colors.WHITE54),
                                ], spacing=5),
                            ], spacing=8),
                            bgcolor="#151B2E",
                            border_radius=12,
                            padding=15,
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.AMBER_400)),
                        ),
                        ft.Container(height=10),
                        ft.Text("هل تم التحويل بالأرباح (في المحفظة) أم تم خصمها (نقداً)؟", size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.RIGHT),
                        ft.Divider(height=10, color=ft.Colors.WHITE10),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "💳 بالأرباح (في المحفظة)",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#14532D",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_new_tx_profit_status(tx, fee_val, "IN_WALLET", custom_dlg),
                                ),
                                ft.ElevatedButton(
                                    "💵 تم خصمها (نقداً)",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#78350F",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_new_tx_profit_status(tx, fee_val, "CASH", custom_dlg),
                                ),
                                ft.ElevatedButton(
                                    "✖ لا يوجد ربح",
                                    color=ft.Colors.WHITE,
                                    bgcolor="#1E293B",
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                    on_click=lambda e: self._set_new_tx_profit_status(tx, fee_val, "NONE", custom_dlg),
                                ),
                                ft.TextButton(
                                    "تحديد لاحقاً / Later",
                                    style=ft.ButtonStyle(color=ft.Colors.WHITE54),
                                    on_click=lambda e: self._close_new_tx_dialog(custom_dlg),
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
            data="new_transaction_dialog",
            alignment=ft.alignment.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            left=0,
            top=0,
            right=0,
            bottom=0,
        )

        self.active_dialog = custom_dlg
        self.root_stack.controls.append(custom_dlg)
        self.page.update()
