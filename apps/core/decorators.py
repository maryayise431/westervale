from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from functools import wraps


def staff_required(view_func=None, login_url='accounts:manager_login'):
    """Require the requesting user to be staff (admin), else redirect away."""

    def decorator(view):
        @wraps(view)
        @login_required(login_url=login_url)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_staff:
                return redirect('dashboard:index')
            return view(request, *args, **kwargs)
        return _wrapped

    if view_func is None:
        return decorator
    return decorator(view_func)


def staff_required_mixin():
    """Decorator factory for class-based admin views."""
    return method_decorator(staff_required, name='dispatch')
