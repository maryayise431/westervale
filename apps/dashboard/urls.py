from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('chart-data/', views.chart_data, name='chart_data'),
    path('portfolio-data/', views.portfolio_data, name='portfolio_data'),
    path('market-data/', views.market_data, name='market_data'),
    path('market-candles/', views.market_candles, name='market_candles'),
]
