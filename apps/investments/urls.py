from django.urls import path

from . import views

app_name = 'investments'

urlpatterns = [
    path('investments/overview/', views.plans_landing, name='landing'),
    path('investments/periodic/', views.plans_periodic, name='periodic'),
    path('investments/flexible/', views.plans_flexible, name='flexible'),
    path('investments/mine/', views.my_investments, name='mine'),
]
