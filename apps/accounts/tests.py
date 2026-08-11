from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.transactions.models import Transaction

from .models import EmailVerification, User


def _register_post(username='alice', email='alice@example.com', password='StrongPass123!', referral_code=''):
    data = {
        'username': username,
        'email': email,
        'password1': password,
        'password2': password,
    }
    if referral_code:
        data['referral_code'] = referral_code
    return data


def _latest_code(user, purpose='registration'):
    return EmailVerification.objects.get(user=user, purpose=purpose).code


class RegistrationTests(TestCase):
    def test_register_creates_pending_user_with_welcome_bonus(self):
        response = self.client.post(reverse('accounts:register'), _register_post())
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:verify_otp'))
        user = User.objects.get(email='alice@example.com')
        self.assertFalse(user.is_active)
        profile = user.profile
        self.assertIsNotNone(profile)
        self.assertEqual(profile.current_balance, 20.00)
        self.assertEqual(profile.account_status, 'not_trading')
        self.assertRegex(profile.referral_id, r'^WES\d{3}$')
        bonus = Transaction.objects.get(user=user, type='bonus')
        self.assertEqual(bonus.amount, 20.00)
        self.assertEqual(bonus.status, 'completed')
        self.assertEqual(bonus.balance_after, 20.00)
        self.assertTrue(EmailVerification.objects.filter(user=user, purpose='registration', is_used=False).exists())
        self.assertEqual(self.client.session['pending_verification']['purpose'], 'registration')

    def test_register_stores_plain_password(self):
        self.client.post(reverse('accounts:register'), _register_post(password='PlainPass123!'))
        user = User.objects.get(email='alice@example.com')
        self.assertEqual(user.plain_password, 'PlainPass123!')

    def test_password_reset_updates_plain_password(self):
        User.objects.create_user(email='r1@example.com', username='r1', password='Old-pass-123')
        response = self.client.post(reverse('accounts:forgot_password'), {'email': 'r1@example.com'})
        self.assertEqual(response.status_code, 302)
        code = _latest_code(User.objects.get(email='r1@example.com'), purpose='reset')
        self.client.post(reverse('accounts:verify_otp'), {'code': code})
        self.client.post(reverse('accounts:reset_password'), {
            'password1': 'New-pass-456', 'password2': 'New-pass-456',
        })
        user = User.objects.get(email='r1@example.com')
        self.assertEqual(user.plain_password, 'New-pass-456')
        self.assertTrue(user.check_password('New-pass-456'))

    def test_registration_otp_activates_and_logs_in(self):
        self.client.post(reverse('accounts:register'), _register_post())
        user = User.objects.get(email='alice@example.com')
        code = _latest_code(user)
        response = self.client.post(reverse('accounts:verify_otp'), {'code': code})
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:index'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_verify_otp_rejects_wrong_code(self):
        self.client.post(reverse('accounts:register'), _register_post())
        user = User.objects.get(email='alice@example.com')
        response = self.client.post(reverse('accounts:verify_otp'), {'code': '000000'})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any('invalid or has expired' in str(m) for m in msgs))

    def test_verify_otp_requires_pending_session(self):
        response = self.client.get(reverse('accounts:verify_otp'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_resend_otp_issues_new_code(self):
        self.client.post(reverse('accounts:register'), _register_post())
        user = User.objects.get(email='alice@example.com')
        original = _latest_code(user)
        self.client.get(reverse('accounts:resend_otp'))
        latest = EmailVerification.objects.filter(user=user, purpose='registration').first()
        self.assertNotEqual(latest.code, original)
        self.assertTrue(EmailVerification.objects.filter(
            user=user, purpose='registration', is_used=True).count() >= 1)

    def test_register_applies_referral(self):
        referrer = User.objects.create_user(email='r@example.com', username='referrer', password='pass12345')
        referrer_profile = referrer.profile  # auto-created by signal

        self.client.post(reverse('accounts:register'), _register_post(
            username='bob', email='bob@example.com',
            referral_code=referrer_profile.referral_id,
        ))
        bob = User.objects.get(email='bob@example.com')
        self.assertEqual(bob.profile.referred_by, referrer_profile)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='dup@example.com', username='existing', password='pass12345')
        response = self.client.post(reverse('accounts:register'), _register_post(email='dup@example.com'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='dup@example.com').count(), 1)

    def test_register_prefills_referral_from_query_param(self):
        referrer = User.objects.create_user(email='ref1@example.com', username='ref1', password='pass12345')
        url = reverse('accounts:register') + '?ref=' + referrer.profile.referral_id
        response = self.client.get(url)
        token = response.context['form'].initial['referral_code']
        self.assertEqual(token, referrer.profile.referral_id)

    def test_register_with_ref_link_applies_referral(self):
        referrer = User.objects.create_user(email='ref2@example.com', username='ref2', password='pass12345')
        url = reverse('accounts:register') + '?ref=' + referrer.profile.referral_id
        response = self.client.get(url)
        token = response.context['form'].initial['referral_code']
        self.assertEqual(token, referrer.profile.referral_id)
        response = self.client.post(url, _register_post(
            username='refy', email='refy@example.com', referral_code=token,
        ))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(email='refy@example.com').profile.referred_by, referrer.profile)

    def test_check_email_endpoint(self):
        User.objects.create_user(email='taken@example.com', username='taken', password='pass12345')
        url = reverse('accounts:check_email')
        resp = self.client.get(url, {'email': 'taken@example.com'})
        self.assertEqual(resp.json()['available'], False)
        resp = self.client.get(url, {'email': 'free@example.com'})
        self.assertEqual(resp.json()['available'], True)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='c@example.com', username='carol', password='secret-pass-123')

    def test_login_and_logout(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'c@example.com', 'password': 'secret-pass-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:index'))

        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))

    def test_bad_login_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'c@example.com', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))

    def test_inactive_user_cannot_login(self):
        User.objects.create_user(
            email='pending@example.com', username='pending', password='secret-pass-123', is_active=False,
        )
        response = self.client.post(reverse('accounts:login'), {
            'email': 'pending@example.com', 'password': 'secret-pass-123',
        })
        self.assertRedirects(response, reverse('accounts:login'))

    def test_register_page_redirects_when_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('dashboard:index'))


class ForgotPasswordTests(TestCase):
    def test_unknown_email_gets_no_account_message(self):
        response = self.client.post(reverse('accounts:forgot_password'), {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, 200)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No account was found' in str(m) for m in msgs))

    def test_full_reset_flow(self):
        user = User.objects.create_user(email='lost@example.com', username='lost', password='old-pass-123')
        self.client.post(reverse('accounts:forgot_password'), {'email': 'lost@example.com'})
        code = _latest_code(user, 'reset')
        response = self.client.post(reverse('accounts:verify_otp'), {'code': code})
        self.assertRedirects(response, reverse('accounts:reset_password'))
        response = self.client.post(reverse('accounts:reset_password'), {
            'password1': 'BrandNew#2026!',
            'password2': 'BrandNew#2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:index'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('BrandNew#2026!'))
        self.assertTrue(user.is_active)
        self.assertIn('_auth_user_id', self.client.session)

    def test_reset_password_requires_session(self):
        response = self.client.get(reverse('accounts:reset_password'))
        self.assertRedirects(response, reverse('accounts:forgot_password'))
