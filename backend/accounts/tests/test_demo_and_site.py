"""Demo helper endpoint, health check and the page that serves the React app."""
from django.urls import reverse
from rest_framework.test import APIClient

from .helpers import ME_URL, AuthTestCase, decode_unverified

EXPIRED_URL = reverse("jwt-demo-expired")


class DemoExpiredTokenTests(AuthTestCase):
    def test_demo_expired_token_is_rejected(self):
        """Demo endpoint returns a correctly signed but expired access token, which the API rejects with 401."""
        access, _ = self.tokens()
        resp = self.bearer(access).get(EXPIRED_URL)
        self.assertEqual(resp.status_code, 200)
        expired = resp.data["expired_access"]
        claims = decode_unverified(expired)
        self.assertEqual(str(claims["user_id"]), str(self.user.pk))
        self.assertEqual(claims["token_type"], "access")
        self.assertEqual(self.bearer(expired).get(ME_URL).status_code, 401)

    def test_demo_expired_token_requires_login(self):
        """Demo endpoint without a token -> 401."""
        self.assertEqual(APIClient().get(EXPIRED_URL).status_code, 401)


class SiteTests(AuthTestCase):
    def test_health_check(self):
        """GET /api/health/ -> 200 without authentication (used by the hosting platform)."""
        resp = APIClient().get(reverse("health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ok")

    def test_frontend_page_is_served(self):
        """GET / -> 200 HTML page (the React app, or a notice if it has not been built)."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("<", resp.content.decode())
