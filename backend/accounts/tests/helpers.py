"""Shared helpers for the authentication tests."""
import base64
import json
from datetime import datetime, timezone

import jwt
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

PASSWORD = "Correct-Horse-42!"

LOGIN_URL = reverse("jwt-login")
REFRESH_URL = reverse("jwt-refresh")
LOGOUT_URL = reverse("jwt-logout")
ME_URL = reverse("jwt-me")
SESSION_LOGIN_URL = reverse("session-login")
SESSION_LOGOUT_URL = reverse("session-logout")
SESSION_ME_URL = reverse("session-me")
DOGS_URL = reverse("dog-breeds")


def now_whole_second():
    """Current UTC time with microseconds removed, for exact freezegun arithmetic."""
    return datetime.now(timezone.utc).replace(microsecond=0)


# --- raw JWT manipulation (what an attacker can do without the signing key) ---

def b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def decode_unverified(token: str) -> dict:
    """Anyone can read a JWT payload: it is base64url-encoded, not encrypted."""
    return json.loads(b64url_decode(token.split(".")[1]))


def decode_header(token: str) -> dict:
    return json.loads(b64url_decode(token.split(".")[0]))


def with_modified_payload(token: str, **changes) -> str:
    """Change claims but keep the original signature."""
    header, payload, signature = token.split(".")
    claims = json.loads(b64url_decode(payload))
    claims.update(changes)
    new_payload = b64url_encode(json.dumps(claims, separators=(",", ":")).encode())
    return f"{header}.{new_payload}.{signature}"


def with_modified_header(token: str, **changes) -> str:
    header, payload, signature = token.split(".")
    h = json.loads(b64url_decode(header))
    h.update(changes)
    return f"{b64url_encode(json.dumps(h, separators=(',', ':')).encode())}.{payload}.{signature}"


def with_corrupted_signature(token: str) -> str:
    # Change the FIRST signature character: the last base64 character can
    # carry only padding bits, so changing it may not change the signature.
    header, payload, signature = token.split(".")
    first = "A" if signature[0] != "A" else "B"
    return f"{header}.{payload}.{first}{signature[1:]}"


def with_alg_none(token: str) -> str:
    """The classic 'alg: none' attack: unsigned token with an empty signature."""
    _, payload, _ = token.split(".")
    header = b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    return f"{header}.{payload}."


def resigned_with(token: str, key: str) -> str:
    """Forge a token: same claims, signed with a key the attacker guessed."""
    return jwt.encode(decode_unverified(token), key, algorithm="HS256")


class AuthTestCase(APITestCase):
    """Creates two users and clears the throttle cache before every test."""

    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.other = User.objects.create_user("bob", "bob@example.com", PASSWORD)

    def login(self, username="alice", password=PASSWORD, client=None):
        client = client or self.client
        return client.post(LOGIN_URL, {"username": username, "password": password}, format="json")

    def tokens(self, username="alice"):
        resp = self.login(username)
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.data["access"], resp.data["refresh"]

    @staticmethod
    def bearer(token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client
