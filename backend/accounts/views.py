"""
Authentication views.

JWT endpoints (stateless, Authorization: Bearer <access token>):
    POST /api/auth/login/    username + password -> access + refresh tokens (throttled)
    POST /api/auth/refresh/  refresh -> new access + new refresh (old refresh blacklisted)
    POST /api/auth/logout/   refresh -> refresh token blacklisted
    GET  /api/auth/me/       the authenticated user

Session endpoints (stateful, sessionid cookie + CSRF token), for comparison:
    POST /api/session/login/
    POST /api/session/logout/
    GET  /api/session/me/
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .demo import make_expired_access_token
from .serializers import CredentialsSerializer, LogoutSerializer, UserSerializer


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
class ThrottledLoginView(TokenObtainPairView):
    """SimpleJWT's login view with a per-IP limit on login attempts."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    """
    Blacklist the caller's refresh token.

    The request must carry a valid access token, and the refresh token in the
    body must belong to the same user, so one user cannot revoke another
    user's session. Note that the access token itself stays valid until it
    expires (at most 5 minutes): JWT access tokens are not checked against
    any server-side store.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Verifies signature, expiry, token type ("refresh") and that the
            # token is not already blacklisted.
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError as exc:
            return Response(
                {"detail": f"Invalid refresh token: {exc}", "code": "token_not_valid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_user_id = str(token.get(jwt_settings.USER_ID_CLAIM))
        request_user_id = str(getattr(request.user, jwt_settings.USER_ID_FIELD))
        if token_user_id != request_user_id:
            return Response(
                {"detail": "This refresh token belongs to a different user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token.blacklist()
        return Response({"detail": "Logged out. The refresh token has been revoked."})


class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class DemoExpiredTokenView(APIView):
    """
    Demo helper for the frontend: returns a correctly signed access token for
    the caller that has ALREADY expired, so the expired-token case can be shown
    without waiting 5 minutes. An expired token grants nothing, so this is safe.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = make_expired_access_token(request.user, minutes_ago=1)
        return Response({"expired_access": str(token), "exp": token["exp"]})


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


# ---------------------------------------------------------------------------
# Session authentication (comparison)
# ---------------------------------------------------------------------------
class SessionLoginView(APIView):
    """
    Log in with a Django session. The server stores the session and the client
    receives an HttpOnly `sessionid` cookie plus a `csrftoken` cookie.

    No authentication class runs here, so DRF does not enforce CSRF on this
    request (a known "login CSRF" trade-off, discussed in the comparison).
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request._request, user)  # creates the server-side session, rotates CSRF token
        return Response(
            {
                "detail": "Logged in with a session.",
                "user": UserSerializer(user).data,
                # Send this back as the X-CSRFToken header on unsafe requests.
                "csrftoken": get_token(request._request),
            }
        )


class SessionLogoutView(APIView):
    """Delete the server-side session. Requires the CSRF token (enforced by SessionAuthentication)."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request._request)  # flushes the session row: the old cookie is now useless
        return Response({"detail": "Logged out. The server-side session was deleted."})


class SessionMeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
