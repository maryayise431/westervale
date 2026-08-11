from decimal import Decimal

from apps.accounts.models import User
from django.test import TestCase
from django.urls import reverse

from apps.transactions.models import Transaction

from .models import Withdrawal


class WithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='w@example.com', username='withdrawer', password='secret-pass-123')
        self.user.profile.current_balance = Decimal('2500.00')
        self.user.profile.save(update_fields=['current_balance'])
        self.client.force_login(self.user)

    def test_request_below_minimum_rejected(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '500', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Withdrawal.objects.count(), 0)

    def test_request_over_balance_rejected(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '5000', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        self.assertEqual(Withdrawal.objects.count(), 0)

    def test_request_wrong_password_rejected(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'wallet_address': 'bc1xyz', 'password': 'wrong-password',
        })
        self.assertEqual(Withdrawal.objects.count(), 0)

    def test_valid_request_creates_pending_withdrawal(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        withdrawal = Withdrawal.objects.get(user=self.user)
        self.assertEqual(withdrawal.amount, Decimal('1200'))
        self.assertEqual(withdrawal.status, 'pending')
        self.assertTrue(withdrawal.password_confirmed)
        # A pending transaction row is logged in history until admin approval
        txn = Transaction.objects.get(user=self.user, type='withdrawal', related_withdrawal=withdrawal)
        self.assertEqual(txn.status, 'pending')
        self.assertIsNone(txn.balance_after)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))

    def test_history_page(self):
        self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        response = self.client.get(reverse('withdrawals:history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1200')
