from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.views import error_preview


class PublicPagesTests(TestCase):
    def test_all_public_pages_render(self):
        cases = [
            ('about', 'About Us'),
            ('services', 'What We Offer'),
            ('how_it_works', 'How It Works'),
            ('public_investments', 'Five stock classes'),
            ('privacy_policy', 'Privacy Policy'),
            ('terms_of_service', 'Terms of Service'),
            ('risk_disclosure', 'Risk Disclosure'),
            ('crypto_page', 'Cryptocurrency'),
            ('forex_page', 'Forex'),
            ('gold_page', 'Gold & Metals'),
            ('real_estate_page', 'Real Estate'),
            ('stocks_page', 'Stocks'),
        ]
        for name, marker in cases:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, marker)

    def test_unknown_asset_page_404s(self):
        response = self.client.get('/investments/nonexistent/')
        self.assertEqual(response.status_code, 404)

    def test_asset_pages_link_to_other_assets(self):
        response = self.client.get(reverse('crypto_page'))
        self.assertContains(response, reverse('forex_page'))
        self.assertContains(response, 'Bitcoin Core')

    def test_homepage_has_social_links_and_page_footer_links(self):
        response = self.client.get(reverse('homepage'))
        self.assertContains(response, 'https://www.instagram.com')
        self.assertContains(response, reverse('privacy_policy'))
        self.assertContains(response, reverse('crypto_page'))
        self.assertContains(response, 'ri-compass-3-line')
        self.assertContains(response, 'ri-tune-line')


class ErrorPagesTests(TestCase):
    @override_settings(DEBUG=False)
    def test_404_page_renders(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page Not Found', status_code=404)

    @override_settings(DEBUG=False)
    def test_500_page_renders(self):
        from django.views.defaults import server_error

        request = RequestFactory().get('/')
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'Something Went Wrong', status_code=500)

    @override_settings(DEBUG=False, MAINTENANCE_MODE=True)
    def test_maintenance_mode_serves_503(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Service Temporarily Unavailable', status_code=503)

    @override_settings(MAINTENANCE_MODE=True)
    def test_admin_still_accessible_in_maintenance_mode(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)

    def test_error_pages_render(self):
        request = RequestFactory().get('/')
        for code, marker in [
            ('400', 'Bad Request'),
            ('403', 'Access Denied'),
            ('404', 'Page Not Found'),
            ('500', 'Something Went Wrong'),
            ('503', 'Service Temporarily Unavailable'),
            ('504', 'Gateway Timeout'),
        ]:
            with self.subTest(code=code):
                response = error_preview(request, code)
                self.assertEqual(response.status_code, int(code))
                self.assertContains(response, marker, status_code=int(code))

    def test_unknown_preview_code_raises_404(self):
        request = RequestFactory().get('/')
        with self.assertRaises(Http404):
            error_preview(request, '999')
