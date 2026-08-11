import uuid

from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.utils import timezone
from apps.deposits.models import Deposit
from apps.investments.models import UserInvestment
from apps.withdrawals.models import Withdrawal


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('profit', 'Profit'),
        ('bonus', 'Bonus'),
        ('referral', 'Referral'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=36, unique=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    balance_after = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    payment_method = models.CharField(max_length=100, blank=True)
    remarks = models.CharField(max_length=255, blank=True)
    related_deposit = models.ForeignKey(Deposit, on_delete=SET_NULL, null=True, blank=True, related_name='transactions')
    related_withdrawal = models.ForeignKey(Withdrawal, on_delete=SET_NULL, null=True, blank=True, related_name='transactions')
    related_investment = models.ForeignKey(UserInvestment, on_delete=SET_NULL, null=True, blank=True, related_name='transactions')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} · {self.get_type_display()} ${self.amount}'
