# backend/licensing/urls.py
from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('validate-license/', views.validate_license, name='validate_license'),
    path('register-trial/', views.register_trial, name='register_trial'),
    path('check-trial-mac/', views.check_trial_mac, name='check_trial_mac'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('use-coupon/', views.use_coupon, name='use_coupon'),
    path('bind-mac/', views.bind_mac, name='bind_mac'),
    path('update-license-status/', views.update_license_status, name='update_license_status'),
    path('login-license/', views.login_license, name='login_license'),
    path('report-unclassified-sms/', views.report_unclassified_sms, name='report_unclassified_sms'),
    path('patterns/', views.get_patterns, name='get_patterns'),
    path('parser-rules/', views.get_parser_rules, name='get_parser_rules'),
    path('transactions/', views.post_transaction, name='post_transaction'),
    path('v1/payment/callback/', api.payment_callback_api, name='payment_callback_api'),
]
