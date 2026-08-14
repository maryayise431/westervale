import secrets
import string
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generate_referral_id():
    return 'WES' + ''.join(secrets.choice(string.digits) for _ in range(3))


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email address must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(_('username'), max_length=30, blank=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)
    plain_password = models.CharField(_('plain password'), max_length=255, blank=True, editable=False)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_plain_password = self.plain_password

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.plain_password = raw_password

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if (update_fields is not None
                and 'plain_password' not in update_fields
                and self.plain_password != self._original_plain_password):
            kwargs['update_fields'] = list(update_fields) + ['plain_password']
        result = super().save(*args, **kwargs)
        self._original_plain_password = self.plain_password
        return result

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_short_name(self):
        return self.username or self.email

    def get_full_name(self):
        full = f'{self.first_name} {self.last_name}'.strip()
        return full or self.username or self.email


class UserProfile(models.Model):
    STATUS_CHOICES = [
        ('trading', 'Trading'),
        ('not_trading', 'Not Trading'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    referral_id = models.CharField(max_length=12, unique=True, default=generate_referral_id, editable=False)
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals'
    )
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    account_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_trading')
    current_balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('0.00'))
    trading_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0.00)
    net_profit = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    amount_invested = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    active_holdings = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} ({self.referral_id})'

    @property
    def total_balance(self):
        return self.current_balance + self.trading_balance

    def apply_referral(self, referral_code):
        if not referral_code:
            return
        try:
            referrer = UserProfile.objects.get(referral_id=referral_code.upper())
        except UserProfile.DoesNotExist:
            return
        if referrer == self:
            return
        self.referred_by = referrer
        self.save(update_fields=['referred_by'])


class EmailVerification(models.Model):
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('reset', 'Password Reset'),
    ]

    OTP_TTL_MINUTES = 10

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verifications'
    )
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} · {self.purpose} · {self.code}'

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
