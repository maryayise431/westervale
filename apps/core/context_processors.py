from django.conf import settings


def site_settings(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'WELCOME_BONUS': settings.WELCOME_BONUS,
        'WITHDRAWAL_MINIMUM': settings.WITHDRAWAL_MINIMUM,
        'PORTFOLIO_REFRESH_INTERVAL_SECONDS': settings.PORTFOLIO_REFRESH_INTERVAL_SECONDS,
    }
