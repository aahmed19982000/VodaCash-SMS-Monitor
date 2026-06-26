# backend/scratch/verify_dashboard_features.py
import os
import sys
import django
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from licensing.models import LicenseKey, MerchantTransaction, CashLedger
from django.test import RequestFactory
from web.views import dashboard_view, dashboard_add_cash_movement, dashboard_update_profit_status, dashboard_delete_cash_movement

def verify_dashboard_logic():
    print("🧪 Verifying central dashboard features...")
    
    # 1. Ensure test user exists
    user, _ = User.objects.get_or_create(username="test_merchant")
    factory = RequestFactory()
    
    # 2. Test dashboard view loading and context data
    print("\n1. Testing dashboard_view loading...")
    request = factory.get('/dashboard/')
    request.user = user
    response = dashboard_view(request)
    assert response.status_code == 200
    print("✅ Dashboard loaded successfully with code 200!")
    
    # 3. Test Add Cash Movement
    print("\n2. Testing dashboard_add_cash_movement API...")
    payload_add = {
        "type": "DEPOSIT",
        "amount": 2500.0,
        "description": "رأس مال إضافي للخزينة"
    }
    request_add = factory.post('/dashboard/cash/add/', data=json.dumps(payload_add), content_type='application/json')
    request_add.user = user
    response_add = dashboard_add_cash_movement(request_add)
    assert response_add.status_code == 200
    data_add = json.loads(response_add.content)
    assert data_add.get("success") is True
    print("✅ Successfully added 2500 EGP deposit into CashLedger!")
    
    # Verify DB record
    record = CashLedger.objects.filter(user=user, type="DEPOSIT", amount=2500.0).first()
    assert record is not None
    print(f"✅ Cash Ledger DB check passed! Record ID: {record.id}")
    
    # 4. Test Update Transaction Profit Status
    print("\n3. Testing dashboard_update_profit_status API...")
    # Find any transaction belonging to user
    tx = MerchantTransaction.objects.filter(user=user).first()
    if tx:
        payload_profit = {
            "transaction_id": tx.transaction_id,
            "profit_status": "CASH"
        }
        request_profit = factory.post('/dashboard/transaction/update-profit/', data=json.dumps(payload_profit), content_type='application/json')
        request_profit.user = user
        response_profit = dashboard_update_profit_status(request_profit)
        assert response_profit.status_code == 200
        data_profit = json.loads(response_profit.content)
        assert data_profit.get("success") is True
        
        # Verify db
        tx.refresh_from_db()
        assert tx.profit_status == "CASH"
        print(f"✅ Successfully updated transaction {tx.transaction_id} profit status to CASH!")
    else:
        print("⚠️ Skipping update-profit test (no transaction found for user).")
        
    # 5. Test Delete Cash Movement
    print("\n4. Testing dashboard_delete_cash_movement API...")
    request_del = factory.post(f'/dashboard/cash/delete/{record.id}/')
    request_del.user = user
    response_del = dashboard_delete_cash_movement(request_del, record.id)
    assert response_del.status_code == 200
    data_del = json.loads(response_del.content)
    assert data_del.get("success") is True
    
    # Verify deletion
    deleted_record = CashLedger.objects.filter(id=record.id).first()
    assert deleted_record is None
    print("✅ Successfully deleted CashLedger record!")
    
    print("\n🚀 All dashboard verification tests passed successfully!")

if __name__ == "__main__":
    verify_dashboard_logic()
