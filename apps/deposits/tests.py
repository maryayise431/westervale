import io
from decimal import Decimal

from PIL import Image
from apps.accounts.models import User
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.investments.models import InvestmentPlan, UserInvestment
from apps.transactions.models import Transaction

from .models import Deposit


def make_image(name='proof.png'):
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class DepositWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='d@example.com', username='depositor', password='secret-pass-123')
        self.plan = InvestmentPlan.objects.create(
            name='Weekly Plan', category='periodic', min_amount=100,
            duration_days=7, duration_label='7 Days', roi_percent=12,
        )
        self.user.profile.current_balance = Decimal('5000.00')
        self.user.profile.save(update_fields=['current_balance'])
        self.client.force_login(self.user)

    def test_initiate_deducts_balance_and_activates_investment(self):
        response = self.client.post(
            reverse('deposits:initiate', args=[self.plan.slug]), {'amount': '500'}
        )
        deposit = Deposit.objects.get(user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('deposits:detail', args=[deposit.pk]))
        self.assertEqual(deposit.amount, Decimal('500'))
        self.assertEqual(deposit.status, 'approved')
        self.assertEqual(deposit.source, 'balance')
        self.assertFalse(deposit.wallet_address_sent_to)
        self.assertEqual(deposit.investment.status, 'active')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('4500.00'))
        self.assertEqual(self.user.profile.trading_balance, Decimal('500.00'))
        txn = Transaction.objects.get(user=self.user)
        self.assertEqual(txn.type, 'investment')
        self.assertEqual(txn.status, 'completed')
        self.assertEqual(txn.amount, Decimal('500'))
        self.assertEqual(txn.balance_after, Decimal('4500.00'))
        self.assertEqual(txn.related_investment, deposit.investment)

    def test_initiate_redirects_to_deposits_when_balance_insufficient(self):
        self.user.profile.current_balance = Decimal('100.00')
        self.user.profile.save(update_fields=['current_balance'])
        response = self.client.post(
            reverse('deposits:initiate', args=[self.plan.slug]), {'amount': '500'}
        )
        self.assertRedirects(response, reverse('deposits:index'))
        self.assertEqual(Deposit.objects.count(), 0)
        self.assertEqual(UserInvestment.objects.count(), 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.current_balance, Decimal('100.00'))

    def test_initiate_rejects_below_minimum(self):
        response = self.client.post(
            reverse('deposits:initiate', args=[self.plan.slug]), {'amount': '10'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Deposit.objects.count(), 0)

    def test_deposit_reference_is_unique_and_formatted(self):
        refs = set()
        for _ in range(10):
            d = Deposit.objects.create(user=self.user, amount=100)
            refs.add(d.reference)
            self.assertRegex(d.reference, r'^[A-Z]{2}\d{4,5}$')
        self.assertEqual(len(refs), 10)

    def test_confirm_requires_image(self):
        deposit = self._create_pending_deposit()
        response = self.client.post(
            reverse('deposits:confirm', args=[deposit.pk]),
            {},
        )
        # No file -> redirect back with error, still no proof
        deposit.refresh_from_db()
        self.assertFalse(bool(deposit.payment_proof))

    def test_confirm_attaches_proof(self):
        deposit = self._create_pending_deposit()
        response = self.client.post(
            reverse('deposits:confirm', args=[deposit.pk]),
            {
                'notes': 'from wallet',
                'payment_proof': make_image(),
            },
        )
        self.assertEqual(response.status_code, 302)
        deposit.refresh_from_db()
        self.assertTrue(bool(deposit.payment_proof))

    def test_confirm_rejects_non_image(self):
        deposit = self._create_pending_deposit()
        fake = SimpleUploadedFile('malware.txt', b'not an image', content_type='text/plain')
        self.client.post(
            reverse('deposits:confirm', args=[deposit.pk]),
            {'payment_proof': fake},
        )
        deposit.refresh_from_db()
        self.assertFalse(bool(deposit.payment_proof))

    def test_confirm_rejects_renamed_fake_image(self):
        deposit = self._create_pending_deposit()
        fake = SimpleUploadedFile('malware.png', b'this is not a real png', content_type='image/png')
        self.client.post(
            reverse('deposits:confirm', args=[deposit.pk]),
            {'payment_proof': fake},
        )
        deposit.refresh_from_db()
        self.assertFalse(bool(deposit.payment_proof))

    def test_confirm_rejects_svg(self):
        deposit = self._create_pending_deposit()
        fake = SimpleUploadedFile('x.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>', content_type='image/svg+xml')
        self.client.post(
            reverse('deposits:confirm', args=[deposit.pk]),
            {'payment_proof': fake},
        )
        deposit.refresh_from_db()
        self.assertFalse(bool(deposit.payment_proof))

    def test_index_get_renders_wallet_cards_and_form(self):
        response = self.client.get(reverse('deposits:index'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('wallet-card', html)
        self.assertIn('name="amount"', html)
        self.assertIn('name="payment_proof"', html)
        self.assertIn('name="wallet_asset"', html)
        self.assertIn('images/btc_qrcode_image.jpeg', html)
        self.assertIn('images/eth_qrcode_image.jpeg', html)
        self.assertNotIn('api.qrserver.com', html)

    def test_index_post_creates_deposit_with_proof(self):
        response = self.client.post(reverse('deposits:index'), {
            'amount': '250',
            'wallet_asset': 'BTC',
            'payment_proof': make_image(),
            'notes': 'test note',
        })
        self.assertEqual(response.status_code, 302)
        deposit = Deposit.objects.get(user=self.user)
        self.assertEqual(deposit.amount, Decimal('250'))
        self.assertEqual(deposit.status, 'pending')
        self.assertIsNone(deposit.investment)
        self.assertTrue(deposit.wallet_address_sent_to)
        self.assertTrue(bool(deposit.payment_proof))
        self.assertEqual(deposit.notes, 'test note')
        txn = Transaction.objects.get(user=self.user, type='deposit', related_deposit=deposit)
        self.assertEqual(txn.status, 'pending')
        self.assertIsNone(txn.balance_after)

    def test_index_rejects_zero_amount(self):
        response = self.client.post(reverse('deposits:index'), {'amount': '0'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Deposit.objects.count(), 0)

    def test_index_rejects_non_numeric_amount(self):
        response = self.client.post(reverse('deposits:index'), {'amount': 'abc'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Deposit.objects.count(), 0)

    def test_index_requires_proof(self):
        response = self.client.post(reverse('deposits:index'), {'amount': '100'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Deposit.objects.count(), 0)

    def test_index_rejects_non_image_proof(self):
        fake = SimpleUploadedFile('x.txt', b'not an image', content_type='text/plain')
        response = self.client.post(reverse('deposits:index'), {
            'amount': '100',
            'payment_proof': fake,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Deposit.objects.count(), 0)

    def test_index_falls_back_to_default_asset_when_invalid(self):
        response = self.client.post(reverse('deposits:index'), {
            'amount': '100',
            'wallet_asset': 'DOGE_NOT_REAL',
            'payment_proof': make_image(),
        })
        self.assertEqual(response.status_code, 302)
        deposit = Deposit.objects.get(user=self.user)
        self.assertEqual(
            deposit.wallet_address_sent_to,
            settings.WALLET_ADDRESSES[settings.DEPOSIT_WALLET_ASSET],
        )

    def test_detail_renders_standalone_deposit(self):
        deposit = Deposit.objects.create(
            user=self.user, amount=100, wallet_address_sent_to='TXabc',
            payment_proof=make_image(),
        )
        response = self.client.get(reverse('deposits:detail', args=[deposit.pk]))
        self.assertEqual(response.status_code, 200)

    def test_history_renders_standalone_deposit(self):
        Deposit.objects.create(user=self.user, amount=100, wallet_address_sent_to='TXabc')
        response = self.client.get(reverse('deposits:history'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('New Deposit', response.content.decode())
        self.assertIn('data:image/png;base64,', response.content.decode())

    def _create_pending_deposit(self):
        inv = UserInvestment.objects.create(
            user=self.user, plan=self.plan, amount_invested=500, status='pending'
        )
        return Deposit.objects.create(
            user=self.user, investment=inv, amount=500, wallet_address_sent_to='TXaddr123'
        )
