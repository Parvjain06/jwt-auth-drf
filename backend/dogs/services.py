"""
Server-side client for The Dog API (https://docs.thedogapi.com/).

The API key is read from settings (environment variable DOG_API_KEY) and is
only ever sent from this server to The Dog API. It never appears in responses
to our own clients. Upstream failures are mapped to clear status codes.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class UpstreamError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _get(path: str, params: dict | None = None):
    url = f"{settings.DOG_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Accept": "application/json"}
    if settings.DOG_API_KEY:
        headers["x-api-key"] = settings.DOG_API_KEY

    try:
        resp = requests.get(url, headers=headers, params=params,
                            timeout=settings.DOG_API_TIMEOUT_SECONDS)
    except requests.Timeout:
        logger.warning("Dog API timed out: %s", url)
        raise UpstreamError(504, "The Dog API did not respond in time.") from None
    except requests.RequestException as exc:
        logger.warning("Dog API unreachable: %s (%s)", url, exc.__class__.__name__)
        raise UpstreamError(502, "Could not reach The Dog API.") from exc

    if resp.status_code == 404:
        raise UpstreamError(404, "Not found at The Dog API.")
    if resp.status_code in (401, 403):
        # Our server's key was rejected. Don't echo upstream details to the client.
        logger.error("Dog API rejected the server's API key (HTTP %s)", resp.status_code)
        raise UpstreamError(502, "The Dog API rejected this server's credentials.")
    if resp.status_code == 429:
        raise UpstreamError(503, "The Dog API rate limit was reached. Try again later.")
    if resp.status_code >= 400:
        logger.warning("Dog API error HTTP %s for %s", resp.status_code, url)
        raise UpstreamError(502, f"The Dog API returned an error (HTTP {resp.status_code}).")

    try:
        return resp.json()
    except ValueError:
        raise UpstreamError(502, "The Dog API returned a response that is not valid JSON.") from None


def _metric(value):
    return value.get("metric") if isinstance(value, dict) else None


def simplify_breed(raw: dict) -> dict:
    """Keep only the fields we expose, so upstream changes don't leak through."""
    image = raw.get("image") if isinstance(raw.get("image"), dict) else {}
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "breed_group": raw.get("breed_group") or None,
        "bred_for": raw.get("bred_for") or None,
        "temperament": raw.get("temperament") or None,
        "life_span": raw.get("life_span") or None,
        "origin": raw.get("origin") or None,
        "weight_kg": _metric(raw.get("weight")),
        "height_cm": _metric(raw.get("height")),
        "image_url": image.get("url"),
        "reference_image_id": raw.get("reference_image_id") or image.get("id"),
    }


def list_breeds(limit: int, page: int) -> list[dict]:
    data = _get("breeds", params={"limit": limit, "page": page})
    if not isinstance(data, list):
        raise UpstreamError(502, "Unexpected response format from The Dog API.")
    return [simplify_breed(b) for b in data if isinstance(b, dict)]


def get_breed(breed_id: int) -> dict:
    data = _get(f"breeds/{breed_id}")
    # The Dog API can answer an unknown id with an empty object instead of 404.
    if not isinstance(data, dict) or not data.get("id"):
        raise UpstreamError(404, "Breed not found.")
    return simplify_breed(data)
