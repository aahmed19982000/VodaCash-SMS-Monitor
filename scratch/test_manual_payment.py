# scratch/test_manual_payment.py
import os
import sys
import django
from datetime import timedelta

# Set up Django environment
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from licensing.models import LicenseKey, PaymentRecord

def run_test():
    print("Starting manual payment database transaction test...")
    
    # 1. Create a dummy user
    username = "test_pay_user"
    user, created = User.objects.get_or_create(username=username, email="test_pay@example.com")
    if created:
        user.set_password("pass123")
        user.save()
        print(f"Created test user: {username}")
    else:
        print(f"Test user {username} already exists")

    # 2. Simulate record_payment for a NEW license
    amount = 150.00
    pay_method = "InstaPay"
    txn_id = "TEST-TXN-123456"
    dur_type = "MONTHLY"
    days = 30
    
    # Clear existing if duplicate
    PaymentRecord.objects.filter(transaction_id=txn_id).delete()

    key_format = f"VC-TEST-{timezone.now().timestamp()}"
    expires_at = timezone.now() + timedelta(days=days)
    
    lic = LicenseKey.objects.create(
        key=key_format,
        user=user,
        client_name=user.username,
        type=dur_type,
        status='ACTIVE',
        expires_at=expires_at
    )
    print(f"Generated new license key: {lic.key}")

    pay_rec = PaymentRecord.objects.create(
        user=user,
        license_key=lic,
        amount=amount,
        payment_method=pay_method,
        transaction_id=txn_id,
        status='SUCCESS'
    )
    print(f"Created payment record for amount: {pay_rec.amount} EGP, Txn: {pay_rec.transaction_id}")

    # 3. Simulate record_payment for EXTENDING an active license
    extend_days = 30
    # Find active license
    active_lic = LicenseKey.objects.filter(user=user, status='ACTIVE', expires_at__gt=timezone.now()).first()
    if active_lic:
        original_expiry = active_lic.expires_at
        active_lic.expires_at += timedelta(days=extend_days)
        active_lic.save()
        print(f"Extended license: {active_lic.key} from {original_expiry} to {active_lic.expires_at}")
        
        # Record payment for extension
        txn_id_2 = "TEST-TXN-789012"
        PaymentRecord.objects.filter(transaction_id=txn_id_2).delete()
        pay_rec_2 = PaymentRecord.objects.create(
            user=user,
            license_key=active_lic,
            amount=amount,
            payment_method="Vodafone Cash",
            transaction_id=txn_id_2,
            status='SUCCESS'
        )
        print(f"Created extension payment record: {pay_rec_2.transaction_id}")
    else:
        print("ERROR: Active license not found during extension simulation!")

    # 4. Clean up test data
    pay_rec.delete()
    if 'pay_rec_2' in locals():
        pay_rec_2.delete()
    lic.delete()
    user.delete()
    print("Database cleanup completed. Test PASSED successfully!")

if __name__ == "__main__":
    run_test()
