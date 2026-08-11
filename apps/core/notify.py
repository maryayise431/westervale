from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.accounts.models import User


def notify_admins(subject, message):
    """Email every staff user about a platform event (fail silently if mail is off)."""
    recipients = list(
        User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True)
    )
    if not recipients:
        return
    context = {
        'site_name': settings.SITE_NAME,
        'subject': subject,
        'message': message,
    }
    email = EmailMultiAlternatives(
        subject,
        render_to_string('emails/admin_notice.txt', context),
        settings.DEFAULT_FROM_EMAIL,
        recipients,
    )
    email.attach_alternative(render_to_string('emails/admin_notice.html', context), 'text/html')
    email.send(fail_silently=True)
