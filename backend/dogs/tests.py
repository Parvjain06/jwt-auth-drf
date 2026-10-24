"""Protected Dog API endpoint. The upstream API is mocked, so tests run offline and deterministically."""
from unittest import mock

import requests
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.helpers import LOGOUT_URL, AuthTestCase, with_corrupted_signature

DOGS_URL = reverse("dog-breeds")
FAKE_KEY = "test-dog-api-key-should-never-leak"

SAMPLE_BREEDS = [
    {
        "id": 1,
        "name": "Affenpinscher",
        "breed_group": "Toy",
        "bred_for": "Small rodent hunting, lapdog",
        "life_span": "10 - 12 years",
        "temperament": "Stubborn, Curious, Playful",
        "origin": "Germany, France",
        "weight": {"imperial": "6 - 13", "metric": "3 - 6"},
        "height": {"imperial": "9 - 11.5", "metric": "23 - 29"},
        "reference_image_id": "BJa4kxc4X",
        "image": {"id": "BJa4kxc4X", "url": "https://cdn2.thedogapi.com/images/BJa4kxc4X.jpg"},
    }
]


def fake_response(status=200, payload=None, bad_json=False):
    resp = mock.Mock()
    resp.status_code = status
    if bad_json:
        resp.json.side_effect = ValueError("not json")
    else:
        resp.json.return_value = payload
    return resp


@override_settings(DOG_API_KEY=FAKE_KEY, DOG_API_BASE_URL="https://api.thedogapi.com/v1")
@mock.patch("dogs.services.requests.get")
class DogEndpointTests(AuthTestCase):
    def authed(self):
        access, _ = self.tokens()
        return self.bearer(access)

    def test_authenticated_request_returns_breeds(self, get):
        """Valid access token -> 200 with simplified breed data from The Dog API."""
        get.return_value = fake_response(payload=SAMPLE_BREEDS)
        resp = self.authed().get(DOGS_URL)
        self.assertEqual(resp.status_code, 200)
        breed = resp.data["results"][0]
        self.assertEqual(breed["name"], "Affenpinscher")
        self.assertEqual(breed["weight_kg"], "3 - 6")
        self.assertNotIn("weight", breed)

    def test_api_key_sent_upstream_but_never_returned(self, get):
        """Server adds x-api-key to the upstream call; the key never appears in our response."""
        get.return_value = fake_response(payload=SAMPLE_BREEDS)
        resp = self.authed().get(DOGS_URL)
        self.assertEqual(get.call_args.kwargs["headers"]["x-api-key"], FAKE_KEY)
        self.assertNotIn(FAKE_KEY, resp.content.decode())
        self.assertNotIn(FAKE_KEY, str(dict(resp.items())))

    def test_missing_token_never_reaches_upstream(self, get):
        """No token -> 401 and The Dog API is not called at all."""
        resp = APIClient().get(DOGS_URL)
        self.assertEqual(resp.status_code, 401)
        get.assert_not_called()

    def test_modified_token_never_reaches_upstream(self, get):
        """Tampered token -> 401 and The Dog API is not called."""
        access, _ = self.tokens()
        resp = self.bearer(with_corrupted_signature(access)).get(DOGS_URL)
        self.assertEqual(resp.status_code, 401)
        get.assert_not_called()

    def test_access_token_still_reaches_dogs_after_logout(self, get):
        """LIMITATION: after logout the unexpired access token can still fetch dog data (200)."""
        get.return_value = fake_response(payload=SAMPLE_BREEDS)
        access, refresh = self.tokens()
        self.bearer(access).post(LOGOUT_URL, {"refresh": refresh}, format="json")
        self.assertEqual(self.bearer(access).get(DOGS_URL).status_code, 200)

    def test_limit_is_clamped(self, get):
        """?limit=500 is clamped to 50 before calling upstream; bad values fall back to defaults."""
        get.return_value = fake_response(payload=[])
        client = self.authed()
        client.get(DOGS_URL, {"limit": 500, "page": -3})
        self.assertEqual(get.call_args.kwargs["params"], {"limit": 50, "page": 0})
        client.get(DOGS_URL, {"limit": "abc"})
        self.assertEqual(get.call_args.kwargs["params"]["limit"], 10)

    def test_breed_detail(self, get):
        """GET /breeds/1/ -> 200 with that breed."""
        get.return_value = fake_response(payload=SAMPLE_BREEDS[0])
        resp = self.authed().get(reverse("dog-breed-detail", args=[1]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], 1)

    def test_breed_detail_not_found(self, get):
        """Unknown breed id (upstream 404 or empty object) -> 404."""
        client = self.authed()
        get.return_value = fake_response(status=404)
        self.assertEqual(client.get(reverse("dog-breed-detail", args=[99999])).status_code, 404)
        get.return_value = fake_response(payload={})
        self.assertEqual(client.get(reverse("dog-breed-detail", args=[99999])).status_code, 404)

    def test_upstream_timeout(self, get):
        """The Dog API times out -> 504 Gateway Timeout."""
        get.side_effect = requests.Timeout()
        resp = self.authed().get(DOGS_URL)
        self.assertEqual(resp.status_code, 504)
        self.assertEqual(resp.data["code"], "upstream_error")

    def test_upstream_unreachable(self, get):
        """The Dog API unreachable (connection error) -> 502 Bad Gateway."""
        get.side_effect = requests.ConnectionError()
        self.assertEqual(self.authed().get(DOGS_URL).status_code, 502)

    def test_upstream_server_error(self, get):
        """The Dog API returns 500 -> 502 Bad Gateway."""
        get.return_value = fake_response(status=500)
        self.assertEqual(self.authed().get(DOGS_URL).status_code, 502)

    def test_upstream_rejects_server_key(self, get):
        """The Dog API returns 401 for our key -> 502, and the client is not told the key."""
        get.return_value = fake_response(status=401)
        resp = self.authed().get(DOGS_URL)
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn(FAKE_KEY, resp.content.decode())

    def test_upstream_rate_limited(self, get):
        """The Dog API returns 429 -> 503 Service Unavailable."""
        get.return_value = fake_response(status=429)
        self.assertEqual(self.authed().get(DOGS_URL).status_code, 503)

    def test_upstream_invalid_json(self, get):
        """The Dog API returns non-JSON -> 502."""
        get.return_value = fake_response(bad_json=True)
        self.assertEqual(self.authed().get(DOGS_URL).status_code, 502)
