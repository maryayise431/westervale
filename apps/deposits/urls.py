from django.urls import path

from . import views

app_name = 'deposits'

urlpatterns = [
    path('deposits/', views.index, name='index'),
    path('deposits/initiate/<slug:plan_slug>/', views.initiate, name='initiate'),
    path('deposits/confirm/<int:deposit_id>/', views.confirm, name='confirm'),
    path('deposits/<int:deposit_id>/', views.detail, name='detail'),
    path('deposits/history/', views.history, name='history'),
]
