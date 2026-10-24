"""Login, token contents and login throttling."""
from django.conf import settings

from .helpers import LOGIN_URL, PASSWORD, AuthTestCase, decode_header, decode_unverified


class LoginTests(AuthTestCase):
    def test_login_success_returns_access_and_refresh(self):
        """Valid credentials -> 200 with an access token and a refresh token."""
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["access"].count("."), 2)  # header.payload.signature

    def test_login_wrong_password(self):
        """Wrong password -> 401, no tokens issued."""
        resp = self.login(password="wrong-password")
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("access", resp.data)

    def test_login_unknown_user(self):
        """Unknown username -> 401 with the same message as a wrong password (no user enumeration)."""
        wrong_pw = self.login(password="wrong-password")
        unknown = self.login(username="nobody")
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.data["detail"], wrong_pw.data["detail"])

    def test_login_missing_fields(self):
        """Missing password field -> 400 validation error."""
        resp = self.client.post(LOGIN_URL, {"username": "alice"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_inactive_user_cannot_log_in(self):
        """Deactivated account -> 401 even with the correct password."""
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)


class TokenContentTests(AuthTestCase):
    def test_access_token_claims_and_lifetime(self):
        """Access token is HS256, type 'access', expires 5 minutes after issue."""
        access, _ = self.tokens()
        header = decode_header(access)
        claims = decode_unverified(access)
        self.assertEqual(header["alg"], "HS256")
        self.assertEqual(claims["token_type"], "access")
        self.assertEqual(claims["exp"] - claims["iat"], 5 * 60)
        self.assertEqual(str(claims["user_id"]), str(self.user.pk))
        self.assertIn("jti", claims)

    def test_refresh_token_claims_and_lifetime(self):
        """Refresh token is type 'refresh' and expires 1 day after issue."""
        _, refresh = self.tokens()
        claims = decode_unverified(refresh)
        self.assertEqual(claims["token_type"], "refresh")
        self.assertEqual(claims["exp"] - claims["iat"], 24 * 60 * 60)

    def test_payload_is_readable_but_holds_no_secrets(self):
        """JWT payload is only base64-encoded: readable by anyone, so it must not contain the password."""
        access, _ = self.tokens()
        claims = decode_unverified(access)
        self.assertEqual(set(claims), {"token_type", "exp", "iat", "jti", "user_id"})
        self.assertNotIn(PASSWORD, str(claims))


class LoginThrottleTests(AuthTestCase):
    def allowed_attempts(self):
        return int(settings.LOGIN_THROTTLE_RATE.split("/")[0])

    def test_repeated_logins_are_throttled(self):
        """After N failed attempts from one IP the next attempt gets 429, even with the right password."""
        for _ in range(self.allowed_attempts()):
            self.assertEqual(self.login(password="guess").status_code, 401)
        resp = self.login()  # correct password, but over the limit
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Retry-After", resp)

    def test_spoofed_x_forwarded_for_does_not_bypass_throttle(self):
        """Sending a different fake X-Forwarded-For per request does not reset the limit (NUM_PROXIES=0)."""
        for i in range(self.allowed_attempts()):
            resp = self.client.post(
                LOGIN_URL, {"username": "alice", "password": "guess"},
                format="json", HTTP_X_FORWARDED_FOR=f"203.0.113.{i}",
            )
            self.assertEqual(resp.status_code, 401)
        resp = self.client.post(
            LOGIN_URL, {"username": "alice", "password": PASSWORD},
            format="json", HTTP_X_FORWARDED_FOR="198.51.100.99",
        )
        self.assertEqual(resp.status_code, 429)
