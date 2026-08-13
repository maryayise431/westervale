from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    METHOD_CHOICES = [
        ('crypto', 'Crypto'),
        ('bank', 'Bank Transfer'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='crypto')
    wallet_address = models.CharField(max_length=255, blank=True)
    bank_account_holder = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_account_type = models.CharField(max_length=50, blank=True)
    bank_routing_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    password_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True,
        related_name='reviewed_withdrawals'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} · ${self.amount} ({self.status})'
