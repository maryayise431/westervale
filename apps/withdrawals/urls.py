from django.urls import path

from . import views

app_name = 'withdrawals'

urlpatterns = [
    path('withdrawals/', views.withdrawal_request, name='request'),
    path('withdrawals/history/', views.withdrawal_history, name='history'),
]
