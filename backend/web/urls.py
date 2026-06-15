# backend/web/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.signup_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('checkout/<str:plan_type>/', views.checkout_view, name='checkout'),
    path('checkout/pending/<str:payment_id>/', views.checkout_pending_view, name='checkout_pending'),
    path('checkout/status/<str:payment_id>/', views.check_payment_status_api, name='check_payment_status'),
    path('backend/login/', views.backend_login_view, name='backend_login'),
    path('backend/logout/', views.backend_logout_view, name='backend_logout'),
    path('backend/', views.admin_panel_view, name='admin_panel'),
    path('download/<str:file_type>/', views.download_file, name='download_file'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('social/login/<str:provider>/', views.social_login_view, name='social_login'),
    path('social/callback/<str:provider>/', views.social_callback_view, name='social_callback'),
]

