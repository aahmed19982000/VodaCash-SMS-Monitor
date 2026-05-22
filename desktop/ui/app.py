# desktop/ui/app.py
import flet as ft
from desktop.db.database import DesktopDatabase
from desktop.ui.views.dashboard_view import DashboardView
from desktop.ui.views.transactions_view import TransactionsView
from desktop.ui.views.settings_view import SettingsView
from desktop.ui.views.phone_search_view import PhoneSearchView
from desktop.ui.views.top_contacts_view import TopContactsView
from desktop.ui.views.calculator_view import CalculatorView

class DesktopApp:
    def __init__(self, page: ft.Page, db: DesktopDatabase, server):
        self.page = page
        self.db = db
        self.server = server

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
            indicator_color=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_400),
            selected_label_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400, size=12),
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

        # Layout
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1, color="#1E293B"),
                    self.view_container,
                ],
                expand=True,
            )
        )

        # تحميل البيانات الأولية في الخلفية لضمان سرعة إقلاع التطبيق
        import threading
        threading.Thread(target=self.refresh_views, daemon=True).start()

    def setup_page(self):
        self.page.title = "VodaCash SMS Monitor"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = "#080C14"
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
            font_family="Segoe UI, Tahoma, Geneva, Verdana, sans-serif"
        )
        self.page.padding = 0
        self.page.window.width = 1250
        self.page.window.height = 820
        self.page.window.min_width = 850
        self.page.window.min_height = 620

        # Add AppBar
        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.MONITOR_HEART_OUTLINED, color=ft.Colors.BLUE_400, size=24),
            leading_width=45,
            title=ft.Text("VodaCash SMS Monitor", weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.WHITE),
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
            self.view_container.content = self.settings_view
        self.page.update()
        
        # تشغيل جلب البيانات في الخلفية لتفادي تعليق الواجهة
        import threading
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
