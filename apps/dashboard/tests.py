from decimal import Decimal

from apps.accounts.models import User
from apps.transactions.models import Transaction
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='dash@example.com', username='dash', password='secret-pass-123')
        self.client.force_login(self.user)

    def _grant_welcome_bonus(self):
        self.user.profile.current_balance = Decimal('20.00')
        self.user.profile.save(update_fields=['current_balance'])
        Transaction.objects.create(
            user=self.user, type='bonus', amount=Decimal('20.00'),
            balance_after=Decimal('20.00'), status='completed',
            payment_method='System', remarks='Welcome bonus',
        )

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_with_bonus_balance(self):
        self._grant_welcome_bonus()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '20.00')
        self.assertContains(response, 'Trading')

    def test_dashboard_does_not_show_removed_charts(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertNotContains(response, 'growthChart')
        self.assertNotContains(response, 'allocationChart')
        self.assertNotContains(response, 'flowChart')
        self.assertNotContains(response, 'Account Growth')
        self.assertNotContains(response, 'Investment Allocation')
        self.assertNotContains(response, 'Deposits vs Withdrawals')

    def test_dashboard_shows_active_investment_performance(self):
        from django.utils import timezone
        from apps.investments.models import InvestmentPlan, UserInvestment
        plan = InvestmentPlan.objects.create(
            name='Starter', category='flexible', min_amount=50,
            duration_days=30, duration_label='30 Days', roi_percent=20,
        )
        profile = self.user.profile
        profile.current_balance = Decimal('100.00')
        profile.trading_balance = Decimal('100.00')
        profile.save(update_fields=['current_balance', 'trading_balance'])
        inv = UserInvestment.objects.create(user=self.user, plan=plan, amount_invested=100)
        inv.activate()
        now = timezone.now()
        inv.start_date = now - timezone.timedelta(days=15)
        inv.maturity_date = inv.start_date + timezone.timedelta(days=30)
        inv.save(update_fields=['start_date', 'maturity_date'])

        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Holding Performance')
        self.assertContains(response, 'Current Value')
        self.assertContains(response, 'Maturity Payout')
        self.assertEqual(len(response.context['active_performances']), 1)
        perf = response.context['active_performances'][0]
        self.assertEqual(perf.progress_pct, 50)
        self.assertEqual(perf.current_value, Decimal('110.00'))

    def test_chart_data_json(self):
        response = self.client.get(reverse('dashboard:chart_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'].startswith('application/json'), True)
        self.assertIn('labels', response.json())

    def test_total_deposits_counts_external_only(self):
        from apps.deposits.models import Deposit
        Deposit.objects.create(user=self.user, amount=Decimal('400'), status='approved', source='external')
        Deposit.objects.create(user=self.user, amount=Decimal('400'), status='approved', source='balance')
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_deposits'], 400.0)
