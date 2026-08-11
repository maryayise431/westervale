from decimal import Decimal

from apps.accounts.models import User
from django.test import TestCase
from django.urls import reverse

from .models import InvestmentPlan, UserInvestment


class InvestmentPlanTests(TestCase):
    def setUp(self):
        self.plan = InvestmentPlan.objects.create(
            name='Test Plan', category='flexible', min_amount=100,
            duration_days=30, duration_label='30 Days', roi_percent=50,
        )

    def test_slug_auto_generated(self):
        self.assertEqual(self.plan.slug, 'test-plan')

    def test_expected_return_percent(self):
        self.assertEqual(self.plan.expected_return_for(1000), Decimal('1500.00'))

    def test_expected_return_fixed(self):
        plan = InvestmentPlan.objects.create(
            name='Fixed Plan', category='periodic', min_amount=50,
            duration_days=7, duration_label='7 Days', return_amount=75,
        )
        self.assertEqual(plan.expected_return_for(100), Decimal('75'))


class InvestmentViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='i@example.com', username='investor', password='secret-pass-123')
        self.plan = InvestmentPlan.objects.create(
            name='Starter', category='flexible', min_amount=50,
            duration_days=30, duration_label='30 Days', roi_percent=20,
        )

    def test_pages_require_login(self):
        for url in ['investments:landing', 'investments:periodic', 'investments:flexible']:
            response = self.client.get(reverse(url))
            self.assertEqual(response.status_code, 302, url)

    def test_plan_pages_render_for_logged_in(self):
        self.client.force_login(self.user)
        for url in ['investments:landing', 'investments:periodic', 'investments:flexible', 'investments:mine']:
            response = self.client.get(reverse(url))
            self.assertEqual(response.status_code, 200, url)

    def test_user_investment_expected_return_auto(self):
        inv = UserInvestment.objects.create(user=self.user, plan=self.plan, amount_invested=500)
        self.assertEqual(inv.expected_return, Decimal('600.00'))

    def test_investment_maturity(self):
        from django.utils import timezone
        inv = UserInvestment.objects.create(user=self.user, plan=self.plan, amount_invested=100)
        inv.activate()
        self.assertEqual(inv.status, 'active')
        self.assertTrue(inv.maturity_date > timezone.now())
        self.assertFalse(inv.is_matured())

    def test_maturity_payout_credits_balance_and_creates_profit(self):
        from django.utils import timezone
        from apps.transactions.models import Transaction
        profile = self.user.profile
        profile.current_balance = Decimal('100.00')
        profile.trading_balance = Decimal('100.00')
        profile.save(update_fields=['current_balance', 'trading_balance'])
        inv = UserInvestment.objects.create(user=self.user, plan=self.plan, amount_invested=100)
        inv.activate()
        inv.maturity_date = timezone.now() - timezone.timedelta(minutes=1)
        inv.save(update_fields=['maturity_date'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('investments:mine'))

        inv.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(inv.status, 'completed')
        profile.refresh_from_db()
        self.assertEqual(profile.current_balance, Decimal('220.00'))
        self.assertEqual(profile.trading_balance, Decimal('0.00'))
        profit = Transaction.objects.get(user=self.user, type='profit')
        self.assertEqual(profit.status, 'completed')
        self.assertEqual(profit.amount, Decimal('120.00'))
        self.assertEqual(profit.balance_after, Decimal('220.00'))
        self.assertEqual(profit.related_investment, inv)

    def test_active_investment_shows_performance_metrics(self):
        from django.utils import timezone
        profile = self.user.profile
        profile.current_balance = Decimal('100.00')
        profile.trading_balance = Decimal('100.00')
        profile.save(update_fields=['current_balance', 'trading_balance'])
        inv = UserInvestment.objects.create(user=self.user, plan=self.plan, amount_invested=100)
        inv.activate()
        now = timezone.now()
        inv.start_date = now - timezone.timedelta(days=15)
        inv.maturity_date = inv.start_date + timezone.timedelta(days=30)
        inv.save(update_fields=['start_date', 'maturity_date'])
        self.client.force_login(self.user)

        response = self.client.get(reverse('investments:mine'))

        self.assertEqual(response.status_code, 200)
        rendered = response.context['investments'][0]
        self.assertEqual(rendered.status, 'active')
        self.assertEqual(rendered.progress_pct, 50)
        self.assertEqual(rendered.day_number, 16)
        self.assertEqual(rendered.days_total, 30)
        self.assertEqual(rendered.days_left, 15)
        self.assertEqual(rendered.current_value, Decimal('110.00'))
        self.assertEqual(len(response.context['active_investments']), 1)
