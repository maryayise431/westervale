import random
import string

from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL
from apps.investments.models import UserInvestment


class Deposit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    SOURCE_CHOICES = [
        ('external', 'External'),
        ('balance', 'Balance'),
    ]

    reference = models.CharField(max_length=8, unique=True, blank=True, editable=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='external')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='deposits')
    investment = models.ForeignKey(
        UserInvestment, on_delete=SET_NULL, null=True, blank=True, related_name='deposits'
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    wallet_address_sent_to = models.CharField(max_length=255, blank=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    transaction_hash = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True,
        related_name='reviewed_deposits'
    )

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def _generate_reference():
        """Unique human-friendly reference: two uppercase letters + 4-5 digits, e.g. DE7678."""
        letters = ''.join(random.choice(string.ascii_uppercase) for _ in range(2))
        digits = ''.join(random.choice(string.digits) for _ in range(random.choice([4, 5])))
        return f'{letters}{digits}'

    def save(self, *args, **kwargs):
        if not self.reference:
            for _ in range(100):
                ref = self._generate_reference()
                if not Deposit.objects.filter(reference=ref).exists():
                    self.reference = ref
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.reference or self.pk} · {self.user.username} · ${self.amount} ({self.status})'
