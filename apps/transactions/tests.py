from apps.accounts.models import User
from django.test import TestCase
from django.urls import reverse

from apps.transactions.models import Transaction


class TransactionHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='t@example.com', username='trader', password='secret-pass-123')
        self.client.force_login(self.user)

    def test_history_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('transactions:history'))
        self.assertEqual(response.status_code, 302)

    def test_history_renders_with_transactions(self):
        Transaction.objects.create(
            user=self.user, type='deposit', amount=100, status='completed',
            remarks='Deposit approved', payment_method='Crypto',
        )
        Transaction.objects.create(
            user=self.user, type='withdrawal', amount=50, status='completed',
            remarks='Withdrawal paid out', payment_method='Crypto',
        )
        response = self.client.get(reverse('transactions:history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deposit approved')
        self.assertContains(response, 'Withdrawal paid out')

    def test_history_filter_by_type(self):
        Transaction.objects.create(user=self.user, type='deposit', amount=100)
        response = self.client.get(reverse('transactions:history'), {'type': 'deposit'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deposit')

    def test_history_search(self):
        Transaction.objects.create(user=self.user, type='bonus', amount=10, remarks='Welcome bonus')
        response = self.client.get(reverse('transactions:history'), {'q': 'Welcome'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome bonus')
