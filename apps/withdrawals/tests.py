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

    def test_crypto_withdrawal_records_method(self):
        self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        withdrawal = Withdrawal.objects.get(user=self.user)
        self.assertEqual(withdrawal.method, 'crypto')
        txn = Transaction.objects.get(user=self.user, type='withdrawal', related_withdrawal=withdrawal)
        self.assertEqual(txn.payment_method, 'Crypto')

    def test_bank_withdrawal_creates_pending_withdrawal(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'method': 'bank',
            'bank_account_holder': 'Jane Doe', 'bank_account_number': '123456789',
            'bank_account_type': 'Checking', 'bank_routing_number': '021000021',
            'bank_name': 'Acme Bank', 'password': 'secret-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        withdrawal = Withdrawal.objects.get(user=self.user)
        self.assertEqual(withdrawal.amount, Decimal('1200'))
        self.assertEqual(withdrawal.status, 'pending')
        self.assertEqual(withdrawal.method, 'bank')
        self.assertEqual(withdrawal.wallet_address, 'Bank Transfer')
        self.assertEqual(withdrawal.bank_account_holder, 'Jane Doe')
        self.assertEqual(withdrawal.bank_account_number, '123456789')
        self.assertEqual(withdrawal.bank_account_type, 'Checking')
        self.assertEqual(withdrawal.bank_routing_number, '021000021')
        self.assertEqual(withdrawal.bank_name, 'Acme Bank')
        txn = Transaction.objects.get(user=self.user, type='withdrawal', related_withdrawal=withdrawal)
        self.assertEqual(txn.payment_method, 'Bank Transfer')

    def test_bank_withdrawal_missing_fields_rejected(self):
        response = self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'method': 'bank',
            'bank_account_holder': 'Jane Doe', 'bank_account_number': '123456789',
            'bank_account_type': 'Checking', 'bank_routing_number': '',
            'bank_name': 'Acme Bank', 'password': 'secret-pass-123',
        })
        self.assertEqual(Withdrawal.objects.count(), 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('2500.00'))

    def test_history_page(self):
        self.client.post(reverse('withdrawals:request'), {
            'amount': '1200', 'wallet_address': 'bc1xyz', 'password': 'secret-pass-123',
        })
        response = self.client.get(reverse('withdrawals:history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1200')
