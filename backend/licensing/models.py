# backend/licensing/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class LicenseKey(models.Model):
    KEY_TYPES = (
        ('TRIAL', 'Trial (فترة تجريبية)'),
        ('MONTHLY', 'Monthly (شهري)'),
        ('YEARLY', 'Yearly (سنوي)'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active (نشط)'),
        ('EXPIRED', 'Expired (منتهي)'),
        ('SUSPENDED', 'Suspended (معطل)'),
    )

    key = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='licenses')
    client_name = models.CharField(max_length=100)
    client_phone = models.CharField(max_length=20, null=True, blank=True)
    type = models.CharField(max_length=10, choices=KEY_TYPES, default='MONTHLY')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    mac_address = models.CharField(max_length=50, null=True, blank=True)
    coupon_used = models.CharField(max_length=50, null=True, blank=True)

    def is_valid(self):
        return self.status == 'ACTIVE' and self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.client_name} - {self.key} ({self.status})"

class Coupon(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    discount_percent = models.FloatField(default=0.0) # Percentage e.g. 50.0
    trial_days = models.IntegerField(default=0) # Additional trial days
    is_active = models.BooleanField(default=True)
    max_uses = models.IntegerField(default=1)
    uses_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.uses_count >= self.max_uses:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% / {self.trial_days} days)"

class PaymentRecord(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending (معلقة)'),
        ('SUCCESS', 'Success (ناجحة)'),
        ('FAILED', 'Failed (فشلت)'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    license_key = models.ForeignKey(LicenseKey, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50) # e.g. Credit Card, Vodafone Cash
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    sender_wallet = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    coupon_code = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.sender_wallet:
            from .utils import normalize_egyptian_phone
            self.sender_wallet = normalize_egyptian_phone(self.sender_wallet)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.amount} EGP ({self.status})"


class UnmatchedTransaction(models.Model):
    raw_sms_body = models.TextField()
    parsed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    parsed_sender = models.CharField(max_length=20)
    parsed_transaction_id = models.CharField(max_length=100, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Unmatched {self.parsed_amount} EGP from {self.parsed_sender} ({self.parsed_transaction_id})"


class SiteConfiguration(models.Model):
    admin_wallet = models.CharField(max_length=20, default="01000000000", verbose_name="محفظة المدير المستلمة")
    gateway_api_key = models.CharField(max_length=100, default="default_key_123456", verbose_name="مفتاح الـ API المشترك للبوابة")
    infobip_api_key = models.CharField(max_length=256, default="", blank=True, verbose_name="Infobip API Key")
    infobip_base_url = models.CharField(max_length=256, default="", blank=True, verbose_name="Infobip Base URL")
    infobip_from_email = models.CharField(max_length=256, default="", blank=True, verbose_name="Infobip From Email")
    resend_api_key = models.CharField(max_length=256, default="", blank=True, verbose_name="Resend API Key")
    resend_from_email = models.CharField(max_length=256, default="onboarding@resend.dev", blank=True, verbose_name="Resend From Email")
    
    whatsapp_enabled = models.BooleanField(default=True, verbose_name="تفعيل إشعارات واتسآب")
    whatsapp_from_number = models.CharField(max_length=50, default="447860088970", blank=True, verbose_name="رقم واتسآب المرسل")
    whatsapp_template_otp = models.CharField(max_length=100, default="test_whatsapp_template_en", blank=True, verbose_name="اسم قالب الـ OTP")
    whatsapp_template_welcome = models.CharField(max_length=100, default="", blank=True, verbose_name="اسم قالب الترحيب والتفعيل")
    whatsapp_template_payment = models.CharField(max_length=100, default="", blank=True, verbose_name="اسم قالب تأكيد الدفع")
    whatsapp_template_language = models.CharField(max_length=10, default="en", verbose_name="لغة القوالب")

    class Meta:
        verbose_name = "إعدادات الموقع"
        verbose_name_plural = "إعدادات الموقع"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "إعدادات الموقع الموحدة"



class UnclassifiedSMSReport(models.Model):
    sender = models.CharField(max_length=50)
    raw_sms = models.TextField()
    received_at = models.DateTimeField(default=timezone.now)
    reported_at = models.DateTimeField(auto_now_add=True)
    mac_address = models.CharField(max_length=50, null=True, blank=True)
    license_key = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return f"{self.sender} - {self.reported_at.strftime('%Y-%m-%d %H:%M')}"


from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    has_whatsapp = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)


class SMSPattern(models.Model):
    pattern_id = models.CharField(max_length=100, unique=True, verbose_name="معرف النمط")
    type = models.CharField(max_length=50, verbose_name="نوع العملية") # e.g. RECEIVED, SENT
    regex_pattern = models.TextField(verbose_name="تعبير Regex")
    groups_json = models.TextField(default="{}", verbose_name="مجموعات التقاط Regex (JSON)")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نمط تحليل الرسائل"
        verbose_name_plural = "أنماط تحليل الرسائل"

    def __str__(self):
        return f"{self.pattern_id} ({self.type})"


class MerchantTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='merchant_transactions', verbose_name="التاجر/المحل")
    license_key = models.ForeignKey(LicenseKey, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="مفتاح الترخيص")
    transaction_id = models.CharField(max_length=100, unique=True, primary_key=True, verbose_name="معرف العملية الفريد")
    type = models.CharField(max_length=50, verbose_name="نوع العملية")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="الرصيد بعد العملية")
    counterpart = models.CharField(max_length=100, blank=True, default='', verbose_name="الطرف الآخر")
    raw_sms = models.TextField(verbose_name="الرسالة الخام")
    parsed_at = models.DateTimeField(verbose_name="وقت التحليل")
    sms_timestamp = models.DateTimeField(verbose_name="وقت الرسالة")
    confidence = models.FloatField(default=1.0, verbose_name="الموثوقية")
    wallet_id = models.CharField(max_length=50, blank=True, default='', verbose_name="معرف المحفظة")
    profit_status = models.CharField(max_length=50, default='UNSET', verbose_name="حالة الربح")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الاستلام على السيرفر")

    class Meta:
        verbose_name = "عملية التاجر"
        verbose_name_plural = "عمليات التجار"
        ordering = ['-sms_timestamp']

    def save(self, *args, **kwargs):
        from .encryption import encrypt_val
        if self.counterpart and not self.counterpart.startswith("gAAAA"):
            self.counterpart = encrypt_val(self.counterpart)
        if self.raw_sms and not self.raw_sms.startswith("gAAAA"):
            self.raw_sms = encrypt_val(self.raw_sms)
        super().save(*args, **kwargs)

    @property
    def decrypted_counterpart(self):
        from .encryption import decrypt_val
        return decrypt_val(self.counterpart)

    @property
    def decrypted_raw_sms(self):
        from .encryption import decrypt_val
        return decrypt_val(self.raw_sms)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_id} ({self.amount} EGP)"


class CashLedger(models.Model):
    MOVEMENT_TYPES = (
        ('DEPOSIT', 'Deposit (إيداع نقدية)'),
        ('WITHDRAWAL', 'Withdrawal (سحب نقدية)'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cash_ledger_records', verbose_name="التاجر")
    type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name="نوع الحركة")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    description = models.TextField(blank=True, default='', verbose_name="الوصف/البيان")
    source_tx_id = models.CharField(max_length=100, blank=True, default='', verbose_name="رمز العملية المرتبطة")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="وقت الحركة")

    class Meta:
        verbose_name = "حركة الخزينة"
        verbose_name_plural = "حركات الخزينة"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.type} ({self.amount} EGP)"




