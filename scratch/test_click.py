import sys
import os
from datetime import datetime

sys.path.append(r"g:\sms\vodacash_monitor")

from desktop.db.database import DesktopDatabase
from desktop.ui.app import DesktopApp
from shared.models import Transaction, TransactionType
import flet as ft

def test_dialog_headless():
    db = DesktopDatabase()
    
    # Mock window
    class MockWindow:
        def __init__(self):
            self.width = 0
            self.height = 0

    # Mock page
    class MockPage:
        def __init__(self):
            self.title = ""
            self.theme_mode = None
            self.bgcolor = ""
            self.theme = None
            self.padding = 0
            self.window = MockWindow()
            self.overlay = []
            self.snack_bar = None
        def add(self, *args, **kwargs):
            pass
        def update(self):
            print("MockPage.update() called!", flush=True)

    # Mock server
    class MockServer:
        connected_clients = 0
    
    page = MockPage()
    print("Instantiating DesktopApp with MockPage...", flush=True)
    app = DesktopApp(page, db, MockServer())
    
    # Create a dummy transaction
    tx = Transaction(
        transaction_id="test_tx_123",
        type=TransactionType.SENT,
        amount=7.00,
        balance_after=100.00,
        counterpart="01012345678",
        raw_sms="تم تحويل 7 جنيه إلى 01012345678",
        wallet_id="vodafone_cash",
    )
    
    print("Calling handle_new_transaction...", flush=True)
    app.handle_new_transaction(tx)
    print("New transaction dialog should be in overlay.", flush=True)
    
    overlay_controls = page.overlay
    print(f"Overlay contains {len(overlay_controls)} controls.", flush=True)
    if len(overlay_controls) > 0:
        container = overlay_controls[0]
        # Let's inspect the buttons and trigger their on_click
        buttons_row = container.content.content.controls[-1]
        print(f"Buttons row: {buttons_row}", flush=True)
        for btn in buttons_row.controls:
            if isinstance(btn, ft.ElevatedButton) or isinstance(btn, ft.TextButton):
                text_val = btn.text if hasattr(btn, 'text') else 'TextButton'
                print(f"Button: {text_val} on_click: {btn.on_click}", flush=True)
                # Try calling the on_click callback
                try:
                    if btn.on_click:
                        print(f"Triggering on_click for {text_val}...", flush=True)
                        class MockEvent:
                            pass
                        event_obj = MockEvent()
                        event_obj.control = btn
                        event_obj.page = page
                        btn.on_click(event_obj)
                        print(f"Successfully clicked {text_val}!", flush=True)
                except Exception as ex:
                    print(f"Error clicking button {text_val}: {ex}", flush=True)
                    import traceback
                    traceback.print_exc()

if __name__ == "__main__":
    test_dialog_headless()
