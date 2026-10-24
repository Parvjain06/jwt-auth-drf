"""Protected-resource access with missing, expired, malformed and modified tokens."""
from datetime import timedelta

from freezegun import freeze_time
from rest_framework.test import APIClient

from .helpers import (
    ME_URL,
    AuthTestCase,
    decode_unverified,
    now_whole_second,
    resigned_with,
    with_alg_none,
    with_corrupted_signature,
    with_modified_header,
    with_modified_payload,
)


class MissingAndMalformedTokenTests(AuthTestCase):
    def test_valid_access_token_grants_access(self):
        """Valid access token -> 200 and the response identifies the token's user."""
        access, _ = self.tokens()
        resp = self.bearer(access).get(ME_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "alice")

    def test_missing_token(self):
        """No Authorization header -> 401 with a 'WWW-Authenticate: Bearer' challenge."""
        resp = APIClient().get(ME_URL)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Bearer", resp["WWW-Authenticate"])

    def test_wrong_auth_scheme(self):
        """'Token <jwt>' instead of 'Bearer <jwt>' -> 401 (header ignored, treated as anonymous)."""
        access, _ = self.tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {access}")
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_bearer_without_token(self):
        """'Bearer' with no token value -> 401."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer")
        self.assertEqual(client.get(ME_URL).status_code, 401)

    def test_garbage_token(self):
        """A random string that is not a JWT -> 401."""
        self.assertEqual(self.bearer("not.a.jwt").get(ME_URL).status_code, 401)

    def test_refresh_token_cannot_be_used_as_access_token(self):
        """Correctly signed refresh token sent as Bearer -> 401 (token_type must be 'access')."""
        _, refresh = self.tokens()
        resp = self.bearer(refresh).get(ME_URL)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["code"], "token_not_valid")


class ExpiryTests(AuthTestCase):
    def test_access_token_expires_after_five_minutes(self):
        """Access token works at 4m59s and is rejected with 401 at 5m01s."""
        with freeze_time(now_whole_second()) as clock:
            access, _ = self.tokens()
            clock.tick(timedelta(minutes=4, seconds=59))
            self.assertEqual(self.bearer(access).get(ME_URL).status_code, 200)
            clock.tick(timedelta(seconds=2))
            resp = self.bearer(access).get(ME_URL)
            self.assertEqual(resp.status_code, 401)
            self.assertEqual(resp.data["code"], "token_not_valid")


class ModifiedTokenTests(AuthTestCase):
    """An attacker holding a valid token tries to change it without the signing key."""

    def assert_rejected(self, token):
        resp = self.bearer(token).get(ME_URL)
        self.assertEqual(resp.status_code, 401, resp.content)
        return resp

    def test_changed_user_id(self):
        """Payload user_id changed to another user (privilege escalation attempt) -> 401."""
        access, _ = self.tokens("alice")
        original = decode_unverified(access)["user_id"]
        forged = with_modified_payload(access, user_id=type(original)(self.other.pk))
        self.assert_rejected(forged)

    def test_extended_expiry(self):
        """Payload exp pushed one year into the future -> 401."""
        access, _ = self.tokens()
        exp = decode_unverified(access)["exp"]
        self.assert_rejected(with_modified_payload(access, exp=exp + 365 * 24 * 3600))

    def test_changed_token_type(self):
        """Refresh token relabelled as 'access' in the payload -> 401."""
        _, refresh = self.tokens()
        self.assert_rejected(with_modified_payload(refresh, token_type="access"))

    def test_corrupted_signature(self):
        """One character of the signature changed -> 401."""
        access, _ = self.tokens()
        self.assert_rejected(with_corrupted_signature(access))

    def test_signature_removed(self):
        """Signature segment stripped (header.payload.) -> 401."""
        access, _ = self.tokens()
        header, payload, _ = access.split(".")
        self.assert_rejected(f"{header}.{payload}.")

    def test_alg_none_attack(self):
        """Header set to alg 'none' with no signature -> 401 (server only accepts HS256)."""
        access, _ = self.tokens()
        self.assert_rejected(with_alg_none(access))

    def test_algorithm_switched_in_header(self):
        """Header alg changed to HS512 with the original signature -> 401."""
        access, _ = self.tokens()
        self.assert_rejected(with_modified_header(access, alg="HS512"))

    def test_token_signed_with_wrong_key(self):
        """Same claims re-signed with a guessed key -> 401."""
        access, _ = self.tokens()
        forged = resigned_with(access, "a-guessed-secret-that-is-at-least-32-bytes")
        self.assert_rejected(forged)

    def test_forged_token_with_wrong_key_and_other_user(self):
        """Forged token claiming another user, signed with a guessed key -> 401."""
        access, _ = self.tokens("alice")
        claims = decode_unverified(access)
        tampered = with_modified_payload(access, user_id=type(claims["user_id"])(self.other.pk))
        self.assert_rejected(resigned_with(tampered, "password1234567890password1234567890"))


class AccountStateTests(AuthTestCase):
    def test_deactivated_user_token_rejected(self):
        """Access token of a user deactivated after login -> 401 (user is checked on each request)."""
        access, _ = self.tokens()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.bearer(access).get(ME_URL).status_code, 401)

    def test_password_change_does_not_revoke_access_token(self):
        """LIMITATION: after a password change the old access token still works until it expires."""
        access, _ = self.tokens()
        self.user.set_password("A-New-Password-99!")
        self.user.save()
        self.assertEqual(self.bearer(access).get(ME_URL).status_code, 200)
