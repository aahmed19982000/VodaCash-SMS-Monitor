# backend/web/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.signup_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/transaction/update-profit/', views.dashboard_update_profit_status, name='dashboard_update_profit'),
    path('dashboard/cash/add/', views.dashboard_add_cash_movement, name='dashboard_add_cash'),
    path('dashboard/cash/delete/<int:record_id>/', views.dashboard_delete_cash_movement, name='dashboard_delete_cash'),
    path('checkout/<str:plan_type>/', views.checkout_view, name='checkout'),
    path('checkout/pending/<str:payment_id>/', views.checkout_pending_view, name='checkout_pending'),
    path('checkout/status/<str:payment_id>/', views.check_payment_status_api, name='check_payment_status'),
    path('backend/login/', views.backend_login_view, name='backend_login'),
    path('backend/logout/', views.backend_logout_view, name='backend_logout'),
    path('backend/', views.admin_panel_view, name='admin_panel'),
    path('backend/api/analyze-sms/', views.admin_api_analyze_sms, name='admin_api_analyze_sms'),
    path('backend/api/save-pattern/', views.admin_api_save_pattern, name='admin_api_save_pattern'),
    path('backend/api/delete-unclassified/', views.admin_api_delete_unclassified, name='admin_api_delete_unclassified'),
    path('download/<str:file_type>/', views.download_file, name='download_file'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('social/login/<str:provider>/', views.social_login_view, name='social_login'),
    path('social/callback/<str:provider>/', views.social_callback_view, name='social_callback'),
]

