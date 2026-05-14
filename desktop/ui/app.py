# desktop/ui/app.py
import flet as ft
from desktop.db.database import DesktopDatabase
from desktop.ui.views.dashboard_view import DashboardView
from desktop.ui.views.transactions_view import TransactionsView
from desktop.ui.views.settings_view import SettingsView

class DesktopApp:
    def __init__(self, page: ft.Page, db: DesktopDatabase):
        self.page = page
        self.db = db
        self.setup_page()

        # Views
        self.dashboard_view = DashboardView(self.page, self.db)
        self.transactions_view = TransactionsView(self.page, self.db)
        self.settings_view = SettingsView(self.page)

        # Navigation
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIST_ALT_OUTLINED,
                    selected_icon=ft.Icons.LIST_ALT,
                    label="Transactions",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Connection",
                ),
            ],
            on_change=self.on_nav_change,
        )

        # Container for the active view
        self.view_container = ft.Container(
            content=self.dashboard_view,
            expand=True,
            padding=10
        )

        # Layout
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1),
                    self.view_container,
                ],
                expand=True,
            )
        )

        # تحميل البيانات الأولية
        self.refresh_views()

    def setup_page(self):
        self.page.title = "VodaCash SMS Monitor"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.window.min_width = 800
        self.page.window.min_height = 600

    def on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.view_container.content = self.dashboard_view
        elif idx == 1:
            self.view_container.content = self.transactions_view
        elif idx == 2:
            self.view_container.content = self.settings_view
        self.refresh_views()

    def refresh_views(self):
        """تحديث الواجهة الحالية بالبيانات الجديدة"""
        if self.view_container.content == self.dashboard_view:
            self.dashboard_view.update_data()
        elif self.view_container.content == self.transactions_view:
            self.transactions_view.update_data()
