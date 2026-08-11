import secrets

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailVerification


def generate_code():
    return f'{secrets.randbelow(1_000_000):06d}'


def send_otp_email(user, code, purpose):
    if purpose == 'registration':
        subject = f'Verify your {settings.SITE_NAME} account'
    else:
        subject = f'{settings.SITE_NAME} password reset code'
    context = {
        'user': user,
        'code': code,
        'purpose': purpose,
        'site_name': settings.SITE_NAME,
        'ttl_minutes': EmailVerification.OTP_TTL_MINUTES,
    }
    email = EmailMultiAlternatives(
        subject,
        render_to_string('emails/otp_email.txt', context),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(render_to_string('emails/otp_email.html', context), 'text/html')
    email.send(fail_silently=True)


def create_and_send_otp(user, purpose):
    """Invalidate old unused codes, generate a fresh one and email it to the user."""
    EmailVerification.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
    code = generate_code()
    verification = EmailVerification.objects.create(
        user=user,
        purpose=purpose,
        code=code,
        expires_at=timezone.now() + timezone.timedelta(minutes=EmailVerification.OTP_TTL_MINUTES),
    )
    send_otp_email(user, code, purpose)
    return verification


def verify_code(user, purpose, code):
    """Validate a submitted code. Returns (ok, error_message). Marks the code used."""
    verification = EmailVerification.objects.filter(
        user=user, purpose=purpose, code=code.strip()
    ).first()
    if verification is None or not verification.is_valid():
        return False, 'The code is invalid or has expired.'
    verification.is_used = True
    verification.save(update_fields=['is_used'])
    return True, ''
