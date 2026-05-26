from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import json
from .models import LicenseKey, Coupon

class LicensingAPITestCase(TestCase):
    def setUp(self):
        # Create a valid license
        self.active_license = LicenseKey.objects.create(
            key="ACTIVE-KEY-123",
            client_name="Test Client",
            type="MONTHLY",
            status="ACTIVE",
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # Create an expired license
        self.expired_license = LicenseKey.objects.create(
            key="EXPIRED-KEY-123",
            client_name="Expired Client",
            type="MONTHLY",
            status="ACTIVE",
            expires_at=timezone.now() - timedelta(days=1)
        )

        # Create a suspended license
        self.suspended_license = LicenseKey.objects.create(
            key="SUSPENDED-KEY-123",
            client_name="Suspended Client",
            type="MONTHLY",
            status="SUSPENDED",
            expires_at=timezone.now() + timedelta(days=30)
        )

        # Create a coupon
        self.valid_coupon = Coupon.objects.create(
            code="SAVE50",
            discount_percent=50.0,
            trial_days=0,
            is_active=True,
            max_uses=10,
            uses_count=0
        )

    def test_validate_license_unbound(self):
        # First time validation: should bind mac address
        response = self.client.post(
            '/api/validate-license/',
            data=json.dumps({"key": "ACTIVE-KEY-123", "mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["license"]["mac_address"], "aa:bb:cc:dd:ee:ff")
        
        # Subsequent validation with same mac should succeed
        response = self.client.post(
            '/api/validate-license/',
            data=json.dumps({"key": "ACTIVE-KEY-123", "mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertTrue(response.json()["success"])

        # Subsequent validation with different mac should fail
        response = self.client.post(
            '/api/validate-license/',
            data=json.dumps({"key": "ACTIVE-KEY-123", "mac_address": "11:22:33:44:55:66"}),
            content_type='application/json'
        )
        self.assertFalse(response.json()["success"])

    def test_validate_license_expired(self):
        response = self.client.post(
            '/api/validate-license/',
            data=json.dumps({"key": "EXPIRED-KEY-123", "mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("منتهي", response.json()["message"])

    def test_validate_license_suspended(self):
        response = self.client.post(
            '/api/validate-license/',
            data=json.dumps({"key": "SUSPENDED-KEY-123", "mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("معطل", response.json()["message"])

    def test_register_trial_only_mac(self):
        response = self.client.post(
            '/api/register-trial/',
            data=json.dumps({"mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("VC-TRIAL-", data["key"])
        
        # Verify it created a license key
        lic = LicenseKey.objects.get(key=data["key"])
        self.assertEqual(lic.mac_address, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(lic.type, "TRIAL")
        
        # Try to register trial again with same MAC address - should fail
        response = self.client.post(
            '/api/register-trial/',
            data=json.dumps({"mac_address": "AA:BB:CC:DD:EE:FF"}),
            content_type='application/json'
        )
        self.assertFalse(response.json()["success"])
        self.assertIn("مسبقاً", response.json()["message"])

    def test_validate_coupon(self):
        # Valid coupon
        response = self.client.post(
            '/api/validate-coupon/',
            data=json.dumps({"code": "save50"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["discount_percent"], 50.0)

        # Invalid coupon
        response = self.client.post(
            '/api/validate-coupon/',
            data=json.dumps({"code": "INVALID"}),
            content_type='application/json'
        )
        self.assertFalse(response.json()["success"])

class WebViewsTestCase(TestCase):
    def test_privacy_policy_view(self):
        response = self.client.get('/privacy-policy/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سياسة الخصوصية لتطبيق "دفتر كاش"')
        self.assertContains(response, 'Privacy Policy for "Daftar Cash"')

    def test_download_file_non_existent(self):
        response = self.client.get('/download/invalid_type/')
        self.assertEqual(response.status_code, 404)

    def test_download_file_exist_or_not(self):
        response_desktop = self.client.get('/download/desktop/')
        self.assertIn(response_desktop.status_code, [200, 404])
        
        response_mobile = self.client.get('/download/mobile/')
        self.assertIn(response_mobile.status_code, [200, 404])

from django.contrib.auth.models import User

class AccountLoginLicensingTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123"
        )
        
        # Create user without license
        self.user_no_lic = User.objects.create_user(
            username="nolicuser",
            email="nolic@example.com",
            password="securepassword123"
        )

        # Create active license bound to user
        self.license = LicenseKey.objects.create(
            key="USER-ACTIVE-KEY-999",
            user=self.user,
            client_name="Test User",
            type="MONTHLY",
            status="ACTIVE",
            expires_at=timezone.now() + timedelta(days=30)
        )

    def test_signup_auto_trial(self):
        # Register a new user via register URL
        response = self.client.post('/register/', data={
            "username": "newclient",
            "email": "newclient@example.com",
            "password": "passwordsome123",
            "password_confirm": "passwordsome123"
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify a user was created and a 7-day trial license was issued
        user = User.objects.get(username="newclient")
        lic = LicenseKey.objects.get(user=user)
        self.assertEqual(lic.type, "TRIAL")
        self.assertEqual(lic.status, "ACTIVE")
        self.assertAlmostEqual(
            lic.expires_at, 
            timezone.now() + timedelta(days=7), 
            delta=timedelta(seconds=10)
        )

    def test_login_license_success(self):
        # Correct credentials, unbound license
        response = self.client.post(
            '/api/login-license/',
            data=json.dumps({
                "username": "testuser",
                "password": "securepassword123",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["license"]["key"], "USER-ACTIVE-KEY-999")
        self.assertEqual(data["license"]["mac_address"], "aa:bb:cc:dd:ee:ff")
        
        # Try logging in with the same MAC address - should succeed
        response = self.client.post(
            '/api/login-license/',
            data=json.dumps({
                "username": "testuser",
                "password": "securepassword123",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            }),
            content_type='application/json'
        )
        self.assertTrue(response.json()["success"])

        # Try logging in with different MAC address - should fail (bound to another device)
        response = self.client.post(
            '/api/login-license/',
            data=json.dumps({
                "username": "testuser",
                "password": "securepassword123",
                "mac_address": "11:22:33:44:55:66"
            }),
            content_type='application/json'
        )
        self.assertFalse(response.json()["success"])
        self.assertIn("مفعل بالفعل على جهاز آخر", response.json()["message"])

    def test_login_license_no_license(self):
        # User has no active license
        response = self.client.post(
            '/api/login-license/',
            data=json.dumps({
                "username": "nolicuser",
                "password": "securepassword123",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("لا يوجد اشتراك نشط", response.json()["message"])

    def test_login_license_wrong_credentials(self):
        # Incorrect password
        response = self.client.post(
            '/api/login-license/',
            data=json.dumps({
                "username": "testuser",
                "password": "wrongpassword",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("غير صحيحة", response.json()["message"])

