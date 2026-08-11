from django.conf import settings
from django.shortcuts import render


class MaintenanceModeMiddleware:
    """Serve the 503 page while the platform is in maintenance mode.

    Enabled with ``DJANGO_MAINTENANCE_MODE=1`` (or ``settings.MAINTENANCE_MODE``).
    Admin routes are exempt so the platform owner can disable maintenance.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MAINTENANCE_MODE:
            path = request.path
            exempt = (
                path.startswith('/admin/')
                or path.startswith('/django-admin/')
                or path.startswith('/static/')
                or path.startswith('/media/')
            )
            if not exempt:
                return render(request, '503.html', status=503)
        return self.get_response(request)


class DevCacheBustMiddleware:
    """Prevent browsers from serving stale static assets during development.

    Django's dev server serves static files without cache headers, which lets
    browsers heuristically cache CSS/JS and hide new changes. This only runs in
    DEBUG so production caching behaviour is untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
