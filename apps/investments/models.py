from decimal import Decimal
import math

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class InvestmentPlan(models.Model):
    CATEGORY_CHOICES = [
        ('periodic', 'Periodic'),
        ('flexible', 'Flexible'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='flexible')
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    min_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0.00)
    duration_days = models.PositiveIntegerField(default=7, help_text='Length of the plan in days')
    duration_label = models.CharField(max_length=50, default='7 Days')
    roi_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.00,
                                      help_text='Return as a percentage of the invested amount')
    return_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0.00,
                                        help_text='Fixed return amount per investment')
    description = models.TextField(blank=True)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'min_amount']

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while InvestmentPlan.objects.filter(slug=slug).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def expected_return_for(self, amount):
        amount = Decimal(str(amount))
        if self.return_amount and self.return_amount > 0:
            return self.return_amount
        return (amount * (Decimal('100') + self.roi_percent) / Decimal('100')).quantize(Decimal('0.01'))

    @property
    def per_1000(self):
        return self.expected_return_for(1000)

    @property
    def badge_icon(self):
        return 'ri-flashlight-line' if self.category == 'periodic' else 'ri-arrow-up-circle-line'


class UserInvestment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investments')
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.PROTECT, related_name='user_investments')
    amount_invested = models.DecimalField(max_digits=16, decimal_places=2)
    expected_return = models.DecimalField(max_digits=16, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    maturity_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} → {self.plan.name}'

    def save(self, *args, **kwargs):
        if self.expected_return == 0 and self.amount_invested:
            self.expected_return = self.plan.expected_return_for(self.amount_invested)
        super().save(*args, **kwargs)

    def activate(self):
        now = timezone.now()
        self.status = 'active'
        self.start_date = now
        self.end_date = now + timezone.timedelta(days=self.plan.duration_days)
        self.maturity_date = self.end_date
        self.save()

    def complete(self):
        self.status = 'completed'
        self.save()

    def is_matured(self):
        return (
            self.status == 'active'
            and self.maturity_date
            and timezone.now() >= self.maturity_date
        )

    @property
    def days_total(self):
        return self.plan.duration_days

    @property
    def progress_pct(self):
        if self.status == 'completed':
            return 100
        if self.status != 'active' or not self.start_date or not self.maturity_date:
            return 0
        total = (self.maturity_date - self.start_date).total_seconds()
        if total <= 0:
            return 0
        elapsed = (timezone.now() - self.start_date).total_seconds()
        return max(0, min(100, int(elapsed / total * 100)))

    @property
    def day_number(self):
        if self.status != 'active' or not self.start_date or not self.maturity_date:
            return 0
        elapsed_days = (timezone.now() - self.start_date).total_seconds() // 86400
        return max(1, min(self.days_total, int(elapsed_days) + 1))

    @property
    def days_left(self):
        if self.status != 'active' or not self.maturity_date:
            return self.days_total
        remaining = (self.maturity_date - timezone.now()).total_seconds() / 86400
        return max(0, int(math.ceil(remaining)))

    @property
    def current_value(self):
        if self.status == 'completed':
            return self.expected_return
        growth = self.expected_return - self.amount_invested
        return (self.amount_invested + growth * Decimal(str(self.progress_pct / 100))).quantize(Decimal('0.01'))
