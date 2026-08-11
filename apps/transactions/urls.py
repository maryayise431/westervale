from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('transactions/', views.transaction_history, name='history'),
]
