from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.deposits.models import Deposit
from apps.investments.models import InvestmentPlan, UserInvestment
from apps.transactions.models import Transaction
from apps.withdrawals.models import Withdrawal

from apps.accounts.models import User
from .models import AuditLog


class AdminPanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='boss@example.com', username='boss', password='admin-pass-123', is_staff=True)
        self.user = User.objects.create_user(email='client@example.com', username='client', password='user-pass-123')
        self.user.profile.current_balance = Decimal('2500.00')
        self.user.profile.save(update_fields=['current_balance'])

    def test_non_staff_redirected_away(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('adminpanel:index'))
        self.assertRedirects(response, reverse('dashboard:index'))

    def test_staff_can_access_index(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('adminpanel:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Users')

    def test_approve_deposit_credits_balance_and_activates(self):
        plan = InvestmentPlan.objects.create(
            name='Plan', category='flexible', min_amount=100,
            duration_days=30, duration_label='30 Days', roi_percent=20,
        )
        inv = UserInvestment.objects.create(
            user=self.user, plan=plan, amount_invested=1000, status='pending'
        )
        deposit = Deposit.objects.create(
            user=self.user, investment=inv, amount=1000, status='pending',
            wallet_address_sent_to='addr',
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:deposit_review', args=[deposit.pk, 'approve'])
        )
        self.assertEqual(response.status_code, 302)

        deposit.refresh_from_db()
        self.assertEqual(deposit.status, 'approved')
        self.assertEqual(deposit.reviewed_by, self.admin)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('3500.00'))
        self.assertEqual(self.user.profile.trading_balance, Decimal('1000.00'))

        inv.refresh_from_db()
        self.assertEqual(inv.status, 'active')

        txn = Transaction.objects.get(user=self.user, type='deposit')
        self.assertEqual(txn.status, 'completed')
        self.assertEqual(txn.balance_after, Decimal('3500.00'))

        self.assertEqual(AuditLog.objects.filter(action='Deposit Approved').count(), 1)

    def test_approve_withdrawal_debits_balance(self):
        withdrawal = Withdrawal.objects.create(
            user=self.user, amount=1500, wallet_address='bc1xyz',
            password_confirmed=True, status='pending',
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:withdrawal_review', args=[withdrawal.pk, 'approve'])
        )
        self.assertEqual(response.status_code, 302)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'approved')

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('1000.00'))

        txn = Transaction.objects.get(user=self.user, type='withdrawal', related_withdrawal=withdrawal)
        self.assertEqual(txn.status, 'completed')
        self.assertEqual(AuditLog.objects.filter(action='Withdrawal Approved').count(), 1)

    def test_withdrawal_list_shows_bank_details(self):
        Withdrawal.objects.create(
            user=self.user, amount=1500, method='bank',
            wallet_address='Bank Transfer',
            bank_account_holder='Client One', bank_account_number='987654321',
            bank_account_type='Savings', bank_routing_number='021000021',
            bank_name='Acme Bank', password_confirmed=True, status='pending',
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('adminpanel:withdrawal_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acme Bank')
        self.assertContains(response, '987654321')
        self.assertContains(response, '021000021')

    def test_approve_deposit_settles_pending_transaction(self):
        deposit = Deposit.objects.create(
            user=self.user, amount=1000, status='pending', wallet_address_sent_to='addr'
        )
        pending = Transaction.objects.create(
            user=self.user, type='deposit', amount=1000, status='pending',
            remarks='Deposit pending verification', related_deposit=deposit,
        )

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:deposit_review', args=[deposit.pk, 'approve'])
        )
        self.assertEqual(response.status_code, 302)

        pending.refresh_from_db()
        self.assertEqual(pending.status, 'completed')
        self.user.profile.refresh_from_db()
        self.assertEqual(pending.balance_after, self.user.profile.current_balance)
        # No duplicate transaction row was appended
        self.assertEqual(
            Transaction.objects.filter(user=self.user, type='deposit', related_deposit=deposit).count(),
            1,
        )

    def test_reject_deposit_marks_pending_transaction_rejected(self):
        deposit = Deposit.objects.create(
            user=self.user, amount=1000, status='pending', wallet_address_sent_to='addr'
        )
        pending = Transaction.objects.create(
            user=self.user, type='deposit', amount=1000, status='pending',
            remarks='Deposit pending verification', related_deposit=deposit,
        )

        self.client.force_login(self.admin)
        self.client.post(
            reverse('adminpanel:deposit_review', args=[deposit.pk, 'reject'])
        )

        pending.refresh_from_db()
        self.assertEqual(pending.status, 'rejected')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))

    def test_reject_deposit_cancels_investment(self):
        plan = InvestmentPlan.objects.create(
            name='Plan2', category='flexible', min_amount=100,
            duration_days=30, duration_label='30 Days', roi_percent=20,
        )
        inv = UserInvestment.objects.create(
            user=self.user, plan=plan, amount_invested=500, status='pending'
        )
        deposit = Deposit.objects.create(
            user=self.user, investment=inv, amount=500, status='pending',
            wallet_address_sent_to='addr',
        )

        self.client.force_login(self.admin)
        self.client.post(reverse('adminpanel:deposit_review', args=[deposit.pk, 'reject']))

        deposit.refresh_from_db()
        self.assertEqual(deposit.status, 'rejected')
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'cancelled')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))

    def test_toggle_trading_status(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:user_toggle_status', args=[self.user.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.account_status, 'trading')
        self.assertEqual(AuditLog.objects.filter(action='Status Toggled').count(), 1)

    def test_transaction_create_syncs_balance(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('adminpanel:transaction_create'), {
            'user': self.user.pk,
            'type': 'bonus',
            'amount': '100',
            'status': 'completed',
            'remarks': 'Manual bonus',
            'payment_method': 'Manual',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2600.00'))
        txn = Transaction.objects.get(user=self.user, type='bonus')
        self.assertEqual(txn.balance_after, Decimal('2600.00'))

    def test_transaction_create_pending_does_not_change_balance(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('adminpanel:transaction_create'), {
            'user': self.user.pk,
            'type': 'bonus',
            'amount': '100',
            'status': 'pending',
            'remarks': 'Manual bonus',
            'payment_method': 'Manual',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))
        txn = Transaction.objects.get(user=self.user, type='bonus')
        self.assertIsNone(txn.balance_after)

    def test_transaction_edit_syncs_balance(self):
        # Create a completed bonus through the editor so its effect is in the balance
        self.client.force_login(self.admin)
        self.client.post(reverse('adminpanel:transaction_create'), {
            'user': self.user.pk,
            'type': 'bonus',
            'amount': '100',
            'status': 'completed',
            'remarks': 'Manual bonus',
        })
        txn = Transaction.objects.get(user=self.user, type='bonus')
        response = self.client.post(reverse('adminpanel:transaction_edit', args=[txn.pk]), {
            'user': self.user.pk,
            'type': 'profit',
            'amount': '250',
            'status': 'completed',
            'created_at': '2026-08-01T10:30',
        })
        self.assertEqual(response.status_code, 302)
        txn.refresh_from_db()
        self.assertEqual(txn.type, 'profit')
        self.assertEqual(txn.amount, Decimal('250'))
        self.assertEqual(txn.created_at.strftime('%Y-%m-%d %H:%M'), '2026-08-01 10:30')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2750.00'))
        self.assertEqual(txn.balance_after, Decimal('2750.00'))

    def test_transaction_delete_reverses_balance(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('adminpanel:transaction_create'), {
            'user': self.user.pk,
            'type': 'bonus',
            'amount': '100',
            'status': 'completed',
        })
        txn = Transaction.objects.get(user=self.user, type='bonus')
        response = self.client.post(reverse('adminpanel:transaction_delete', args=[txn.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=txn.pk).exists())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))

    def test_admin_balance_edit_updates_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('adminpanel:user_detail', args=[self.user.pk]), {
            'current_balance': '5000.00',
            'trading_balance': '100.00',
            'net_profit': '250.00',
            'amount_invested': '800.00',
            'active_holdings': '3',
            'account_status': 'not_trading',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('5000.00'))
        self.assertEqual(self.user.profile.trading_balance, Decimal('100.00'))
        self.assertEqual(self.user.profile.net_profit, Decimal('250.00'))
        self.assertEqual(self.user.profile.amount_invested, Decimal('800.00'))
        self.assertEqual(self.user.profile.active_holdings, 3)
        self.assertEqual(self.user.profile.account_status, 'not_trading')
        self.assertEqual(AuditLog.objects.filter(action='Balance Updated').count(), 5)

    def test_admin_balance_edit_auto_clears_override(self):
        self.user.profile.net_profit = Decimal('999.00')
        self.user.profile.amount_invested = Decimal('999.00')
        self.user.profile.active_holdings = 9
        self.user.profile.save()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('adminpanel:user_detail', args=[self.user.pk]), {
            'current_balance': '5000.00',
            'trading_balance': '0.00',
            'net_profit_auto': 'on',
            'amount_invested_auto': 'on',
            'active_holdings_auto': 'on',
            'account_status': 'not_trading',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.net_profit)
        self.assertIsNone(self.user.profile.amount_invested)
        self.assertIsNone(self.user.profile.active_holdings)

    def test_set_user_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:user_set_password', args=[self.user.pk]),
            {'password1': 'new-pass-456', 'password2': 'new-pass-456'},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-pass-456'))
        self.assertEqual(self.user.plain_password, 'new-pass-456')
        self.assertEqual(AuditLog.objects.filter(action='Password Reset').count(), 1)

    def test_user_detail_displays_plain_password(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('adminpanel:user_detail', args=[self.user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.plain_password)
        self.assertContains(response, 'Current password')

    def test_set_user_password_mismatch_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('adminpanel:user_set_password', args=[self.user.pk]),
            {'password1': 'new-pass-456', 'password2': 'different-789'},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('new-pass-456'))
        self.assertTrue(self.user.check_password('user-pass-123'))
        self.assertEqual(AuditLog.objects.filter(action='Password Reset').count(), 0)

    def test_staff_cannot_use_customer_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': self.admin.email, 'password': 'admin-pass-123',
        })
        self.assertRedirects(response, reverse('accounts:manager_login'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ManagerCreationViaAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email='root@example.com', username='root', password='root-pass-123'
        )

    def test_group_add_form_creates_staff_user(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin:auth_group_add'), {
            'name': 'Account Manager',
            'email': 'manager@example.com',
            'password1': 'mgr-pass-123',
            'password2': 'mgr-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        group = Group.objects.get(name='Account Manager')
        user = User.objects.get(email='manager@example.com')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.first_name, 'Account Manager')
        self.assertIn(group, user.groups.all())
        self.assertTrue(User.objects.filter(profile__isnull=False, email=user.email).exists())

    def test_created_manager_can_reach_admin_panel(self):
        self.client.force_login(self.superuser)
        self.client.post(reverse('admin:auth_group_add'), {
            'name': 'Ops',
            'email': 'ops@example.com',
            'password1': 'ops-pass-123',
            'password2': 'ops-pass-123',
        })
        self.client.logout()
        ok = self.client.login(email='ops@example.com', password='ops-pass-123')
        self.assertTrue(ok)
        response = self.client.get(reverse('adminpanel:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Users')

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='taken@example.com', username='taken', password='x')
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin:auth_group_add'), {
            'name': 'Taker',
            'email': 'taken@example.com',
            'password1': 'abc-123',
            'password2': 'abc-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Group.objects.filter(name='Taker').exists())

    def test_password_mismatch_rejected(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin:auth_group_add'), {
            'name': 'Mismatch',
            'email': 'mm@example.com',
            'password1': 'abc-123',
            'password2': 'abc-124',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Group.objects.filter(name='Mismatch').exists())
        self.assertFalse(User.objects.filter(email='mm@example.com').exists())
