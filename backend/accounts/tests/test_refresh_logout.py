"""Token refresh, rotation, logout (blacklisting) and post-logout behaviour."""
from datetime import timedelta

from freezegun import freeze_time
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .helpers import (
    LOGOUT_URL,
    ME_URL,
    REFRESH_URL,
    AuthTestCase,
    decode_unverified,
    now_whole_second,
)


class RefreshTests(AuthTestCase):
    def refresh(self, token):
        return APIClient().post(REFRESH_URL, {"refresh": token}, format="json")

    def test_refresh_issues_new_access_and_rotated_refresh(self):
        """Valid refresh -> 200 with a new access token AND a new refresh token (rotation)."""
        access, refresh = self.tokens()
        resp = self.refresh(refresh)
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.data["access"], access)
        self.assertIn("refresh", resp.data)
        self.assertNotEqual(resp.data["refresh"], refresh)
        self.assertEqual(self.bearer(resp.data["access"]).get(ME_URL).status_code, 200)

    def test_old_refresh_token_rejected_after_rotation(self):
        """Reusing a refresh token that was already rotated -> 401 (it was blacklisted)."""
        _, refresh = self.tokens()
        self.assertEqual(self.refresh(refresh).status_code, 200)
        resp = self.refresh(refresh)
        self.assertEqual(resp.status_code, 401)
        jti = decode_unverified(refresh)["jti"]
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=jti).exists())

    def test_access_token_cannot_be_used_to_refresh(self):
        """Access token sent to /refresh/ -> 401 (wrong token type)."""
        access, _ = self.tokens()
        self.assertEqual(self.refresh(access).status_code, 401)

    def test_invalid_refresh_token(self):
        """Garbage refresh token -> 401."""
        self.assertEqual(self.refresh("abc.def.ghi").status_code, 401)

    def test_refresh_token_expires_after_one_day(self):
        """Refresh token works at 23h59m and is rejected with 401 at 24h01m."""
        with freeze_time(now_whole_second()) as clock:
            _, refresh_a = self.tokens()   # two logins at the same instant
            _, refresh_b = self.tokens()
            clock.tick(timedelta(hours=23, minutes=59))
            self.assertEqual(self.refresh(refresh_a).status_code, 200)
            clock.tick(timedelta(minutes=2))
            self.assertEqual(self.refresh(refresh_b).status_code, 401)

    def test_rotation_gives_a_fresh_one_day_lifetime(self):
        """Rotated refresh token gets a full new 1-day lifetime (sliding expiry), later than the original."""
        with freeze_time(now_whole_second()) as clock:
            _, refresh = self.tokens()
            clock.tick(timedelta(hours=12))
            new_refresh = self.refresh(refresh).data["refresh"]
        old, new = decode_unverified(refresh), decode_unverified(new_refresh)
        self.assertEqual(new["exp"] - new["iat"], 24 * 60 * 60)
        self.assertEqual(new["exp"] - old["exp"], 12 * 60 * 60)

    def test_login_records_outstanding_refresh_token(self):
        """Each login stores the refresh token's jti server-side (OutstandingToken) so it can be blacklisted."""
        _, refresh = self.tokens()
        jti = decode_unverified(refresh)["jti"]
        self.assertTrue(OutstandingToken.objects.filter(jti=jti, user=self.user).exists())


class LogoutTests(AuthTestCase):
    def logout(self, access, refresh):
        return self.bearer(access).post(LOGOUT_URL, {"refresh": refresh}, format="json")

    def test_logout_blacklists_refresh_token(self):
        """Logout -> 200 and the refresh token's jti is in the blacklist table."""
        access, refresh = self.tokens()
        resp = self.logout(access, refresh)
        self.assertEqual(resp.status_code, 200)
        jti = decode_unverified(refresh)["jti"]
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=jti).exists())

    def test_refresh_token_reuse_after_logout(self):
        """Refresh token used after logout -> 401 'Token is blacklisted'."""
        access, refresh = self.tokens()
        self.logout(access, refresh)
        resp = APIClient().post(REFRESH_URL, {"refresh": refresh}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_access_token_still_works_after_logout(self):
        """LIMITATION: an unexpired access token keeps working after logout (200 on /me and /dogs)."""
        access, refresh = self.tokens()
        self.assertEqual(self.logout(access, refresh).status_code, 200)
        self.assertEqual(self.bearer(access).get(ME_URL).status_code, 200)
        # The Dog API endpoint would also accept it; checked in dogs.tests with a mocked upstream.

    def test_access_token_stops_working_when_it_expires_after_logout(self):
        """After logout the access token is accepted until its 5-minute expiry, then rejected (401)."""
        with freeze_time(now_whole_second()) as clock:
            access, refresh = self.tokens()
            clock.tick(timedelta(minutes=1))
            self.assertEqual(self.logout(access, refresh).status_code, 200)
            clock.tick(timedelta(minutes=3, seconds=58))   # 4m58s after issue
            self.assertEqual(self.bearer(access).get(ME_URL).status_code, 200)
            clock.tick(timedelta(seconds=3))               # 5m01s after issue
            self.assertEqual(self.bearer(access).get(ME_URL).status_code, 401)

    def test_logout_twice(self):
        """Second logout with the same refresh token -> 400 (already blacklisted)."""
        access, refresh = self.tokens()
        self.assertEqual(self.logout(access, refresh).status_code, 200)
        self.assertEqual(self.logout(access, refresh).status_code, 400)

    def test_logout_requires_access_token(self):
        """Logout without an access token -> 401, and the refresh token stays valid."""
        _, refresh = self.tokens()
        resp = APIClient().post(LOGOUT_URL, {"refresh": refresh}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(APIClient().post(REFRESH_URL, {"refresh": refresh}, format="json").status_code, 200)

    def test_cannot_log_out_another_user(self):
        """Alice sending Bob's refresh token to logout -> 403, Bob's token is not revoked."""
        alice_access, _ = self.tokens("alice")
        _, bob_refresh = self.tokens("bob")
        self.assertEqual(self.logout(alice_access, bob_refresh).status_code, 403)
        self.assertEqual(APIClient().post(REFRESH_URL, {"refresh": bob_refresh}, format="json").status_code, 200)

    def test_logout_missing_refresh_field(self):
        """Logout body without 'refresh' -> 400."""
        access, _ = self.tokens()
        resp = self.bearer(access).post(LOGOUT_URL, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_logout_with_access_token_in_body(self):
        """Access token supplied where the refresh token belongs -> 400 (wrong token type)."""
        access, _ = self.tokens()
        self.assertEqual(self.logout(access, access).status_code, 400)

    def test_logout_does_not_affect_other_sessions(self):
        """Logging out one login (device) leaves the refresh token of another login usable."""
        access1, refresh1 = self.tokens()
        _, refresh2 = self.tokens()
        self.logout(access1, refresh1)
        self.assertEqual(APIClient().post(REFRESH_URL, {"refresh": refresh2}, format="json").status_code, 200)
