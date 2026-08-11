from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    wallet_address = models.CharField(max_length=255)
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
