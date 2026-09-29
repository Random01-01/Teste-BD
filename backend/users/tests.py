from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    CSRF_TRUSTED_ORIGINS=['https://aura-preview.example'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class CsrfRegressionTests(TestCase):
    def setUp(self):
        cache.clear()  # Isolate per-request throttle state between test cases.
        self.user = get_user_model().objects.create_user('csrf-test@example.com', 'Only-for-tests!7349')
        self.client = APIClient(enforce_csrf_checks=True)
        self.credentials = {'email': self.user.email, 'password': 'Only-for-tests!7349'}
        self.origin = 'https://aura-preview.example'

    def token(self):
        response = self.client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('Cookie', response['Vary'])
        return response.data['csrfToken']

    def post(self, path, data, token, origin=None):
        return self.client.post(path, data, format='json', HTTP_X_CSRFTOKEN=token,
                                HTTP_ORIGIN=origin or self.origin)

    def test_header_without_cookie_is_not_accepted_for_login_or_reset(self):
        token = self.token()
        self.client.cookies.clear()
        for path, data in [('/api/auth/login/', self.credentials),
                           ('/api/auth/password-reset/', {'email': self.user.email})]:
            response = self.post(path, data, token)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['code'], 'csrf_failed')
            self.assertEqual(response.json()['csrfReason'], 'cookie_missing')
        self.user.refresh_from_db()
        self.assertIsNone(self.user.last_login)

    def test_trusted_preview_login_and_password_reset_work_with_real_cookie(self):
        token = self.token()
        response = self.post('/api/auth/login/', self.credentials, token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(settings.SESSION_COOKIE_NAME, self.client.cookies)
        self.assertIn('no-store', response['Cache-Control'])
        response = self.post('/api/auth/password-reset/', {'email': 'missing@example.com'}, response.data['csrfToken'])
        self.assertEqual(response.status_code, 200)

    def test_untrusted_origin_still_rejected_with_a_valid_token(self):
        token = self.token()
        response = self.post('/api/auth/login/', self.credentials, token, 'https://evil.example')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['csrfReason'], 'origin_rejected')
        self.assertNotIn('evil.example', str(response.json()))

    def test_rotation_rejects_stale_token_then_allows_refreshed_token(self):
        stale = self.token()
        self.assertEqual(self.post('/api/auth/login/', self.credentials, stale).status_code, 200)
        response = self.post('/api/notifications/read_all/', {}, stale)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'csrf_failed')
        self.assertEqual(response.json()['csrfReason'], 'token_invalid')
        self.assertEqual(self.post('/api/notifications/read_all/', {}, self.token()).status_code, 200)

    def test_invalid_credentials_are_not_a_csrf_error(self):
        response = self.post('/api/auth/login/', {**self.credentials, 'password': 'incorrect'}, self.token())
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('code', response.json())
