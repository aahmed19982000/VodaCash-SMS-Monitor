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
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('download/<str:file_type>/', views.download_file, name='download_file'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
]
