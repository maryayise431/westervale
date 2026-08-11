from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('manager/login/', views.manager_login_view, name='manager_login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('verify-otp/resend/', views.resend_otp_view, name='resend_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('check-email/', views.check_email, name='check_email'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.change_password_view, name='change_password'),
]
