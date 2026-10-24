"""Django session authentication, and a side-by-side revocation comparison with JWT."""
from django.contrib.sessions.models import Session
from rest_framework.test import APIClient

from .helpers import (
    LOGOUT_URL,
    ME_URL,
    PASSWORD,
    SESSION_LOGIN_URL,
    SESSION_LOGOUT_URL,
    SESSION_ME_URL,
    AuthTestCase,
)


class SessionAuthTests(AuthTestCase):
    def session_login(self, client, password=PASSWORD):
        return client.post(SESSION_LOGIN_URL, {"username": "alice", "password": password}, format="json")

    def test_session_login_sets_httponly_cookie(self):
        """Session login -> 200, server stores a session and sets an HttpOnly 'sessionid' cookie."""
        client = APIClient()
        resp = self.session_login(client)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("sessionid", resp.cookies)
        self.assertTrue(resp.cookies["sessionid"]["httponly"])
        self.assertEqual(Session.objects.count(), 1)

    def test_session_login_wrong_password(self):
        """Session login with wrong password -> 401, no session created."""
        resp = self.session_login(APIClient(), password="wrong")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(Session.objects.count(), 0)

    def test_session_cookie_grants_access(self):
        """Browser-style client sending the session cookie -> 200 on the session-protected endpoint."""
        client = APIClient()
        self.session_login(client)
        self.assertEqual(client.get(SESSION_ME_URL).status_code, 200)

    def test_session_endpoint_without_cookie(self):
        """No session cookie -> 403 (DRF SessionAuthentication sends no auth challenge, so 403 not 401)."""
        self.assertEqual(APIClient().get(SESSION_ME_URL).status_code, 403)

    def test_session_logout_requires_csrf_token(self):
        """Session logout without the X-CSRFToken header -> 403; with it -> 200."""
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.session_login(client).status_code, 200)
        self.assertEqual(client.post(SESSION_LOGOUT_URL).status_code, 403)
        csrf = client.cookies["csrftoken"].value
        self.assertEqual(client.post(SESSION_LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf).status_code, 200)

    def test_jwt_endpoint_needs_no_csrf_token(self):
        """JWT in the Authorization header is not sent automatically by browsers, so no CSRF token is needed."""
        access, refresh = self.tokens()
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(client.post(LOGOUT_URL, {"refresh": refresh}, format="json").status_code, 200)

    def test_stolen_session_cookie_is_useless_after_logout(self):
        """Session logout deletes the server-side session: a copied cookie -> 403 immediately."""
        client = APIClient()
        self.session_login(client)
        stolen = client.cookies["sessionid"].value
        self.assertEqual(client.post(SESSION_LOGOUT_URL).status_code, 200)
        self.assertEqual(Session.objects.count(), 0)

        attacker = APIClient()
        attacker.cookies["sessionid"] = stolen
        self.assertEqual(attacker.get(SESSION_ME_URL).status_code, 403)


class RevocationComparisonTests(AuthTestCase):
    def test_logout_revocation_session_vs_jwt(self):
        """COMPARISON: after logout a copied session cookie fails at once (403); a copied JWT access token still works (200)."""
        # Session
        browser = APIClient()
        browser.post(SESSION_LOGIN_URL, {"username": "alice", "password": PASSWORD}, format="json")
        copied_cookie = browser.cookies["sessionid"].value
        browser.post(SESSION_LOGOUT_URL)
        session_attacker = APIClient()
        session_attacker.cookies["sessionid"] = copied_cookie

        # JWT
        access, refresh = self.tokens()
        self.bearer(access).post(LOGOUT_URL, {"refresh": refresh}, format="json")
        jwt_attacker = self.bearer(access)

        self.assertEqual(session_attacker.get(SESSION_ME_URL).status_code, 403)
        self.assertEqual(jwt_attacker.get(ME_URL).status_code, 200)

    def test_jwt_validation_needs_no_server_state_but_sessions_do(self):
        """COMPARISON: deleting all sessions logs session users out; JWT access tokens keep validating (stateless)."""
        browser = APIClient()
        browser.post(SESSION_LOGIN_URL, {"username": "alice", "password": PASSWORD}, format="json")
        access, _ = self.tokens()

        Session.objects.all().delete()   # e.g. session store wiped or server-side revocation

        self.assertEqual(browser.get(SESSION_ME_URL).status_code, 403)
        self.assertEqual(self.bearer(access).get(ME_URL).status_code, 200)
