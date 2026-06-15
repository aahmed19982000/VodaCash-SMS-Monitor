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


