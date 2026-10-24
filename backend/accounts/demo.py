from datetime import timedelta

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.utils import aware_utcnow


def make_expired_access_token(user, minutes_ago: int = 1) -> AccessToken:
    """A correctly signed access token for `user` that expired `minutes_ago` minutes ago."""
    token = AccessToken.for_user(user)
    issued = aware_utcnow() - token.lifetime - timedelta(minutes=minutes_ago)
    token.set_iat(at_time=issued)
    token.set_exp(from_time=issued)
    return token
