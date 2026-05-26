from django.contrib import admin
from .models import LicenseKey, Coupon, PaymentRecord, UnclassifiedSMSReport

@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'client_name', 'type', 'status', 'expires_at', 'mac_address')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('key', 'client_name', 'client_phone', 'mac_address')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'trial_days', 'is_active', 'max_uses', 'uses_count')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('code',)

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_key', 'amount', 'payment_method', 'transaction_id', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('transaction_id', 'user__username')

@admin.register(UnclassifiedSMSReport)
class UnclassifiedSMSReportAdmin(admin.ModelAdmin):
    list_display = ('sender', 'reported_at', 'mac_address', 'license_key')
    list_filter = ('reported_at', 'sender')
    search_fields = ('sender', 'raw_sms', 'mac_address', 'license_key')

