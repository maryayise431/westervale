from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import asset_page, error_preview, homepage, page
from config.admin import manager_admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('django-admin/', manager_admin.urls),

    path('', homepage, name='homepage'),
    path('about/', page, {'name': 'about'}, name='about'),
    path('services/', page, {'name': 'services'}, name='services'),
    path('how-it-works/', page, {'name': 'how_it_works'}, name='how_it_works'),
    path('investments/', page, {'name': 'investments'}, name='public_investments'),
    path('privacy-policy/', page, {'name': 'privacy_policy'}, name='privacy_policy'),
    path('terms-of-service/', page, {'name': 'terms_of_service'}, name='terms_of_service'),
    path('risk-disclosure/', page, {'name': 'risk_disclosure'}, name='risk_disclosure'),
    path('investments/cryptocurrency/', asset_page, {'slug': 'cryptocurrency'}, name='crypto_page'),
    path('investments/forex/', asset_page, {'slug': 'forex'}, name='forex_page'),
    path('investments/gold-metals/', asset_page, {'slug': 'gold_metals'}, name='gold_page'),
    path('investments/real-estate/', asset_page, {'slug': 'real_estate'}, name='real_estate_page'),
    path('investments/stocks/', asset_page, {'slug': 'stocks'}, name='stocks_page'),

    path('dashboard/', include('apps.dashboard.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.investments.urls')),
    path('', include('apps.deposits.urls')),
    path('', include('apps.withdrawals.urls')),
    path('', include('apps.transactions.urls')),
    path('admin-panel/', include('apps.adminpanel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('preview/<str:code>/', error_preview, name='error_preview')]
