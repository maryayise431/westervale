from django.urls import path

from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('', views.index, name='index'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/set-password/', views.user_set_password, name='user_set_password'),
    path('deposits/', views.deposit_list, name='deposit_list'),
    path('deposits/<int:pk>/', views.deposit_detail, name='deposit_detail'),
    path('deposits/<int:pk>/<str:action>/', views.deposit_review, name='deposit_review'),
    path('withdrawals/', views.withdrawal_list, name='withdrawal_list'),
    path('withdrawals/<int:pk>/<str:action>/', views.withdrawal_review, name='withdrawal_review'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_edit, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
]
