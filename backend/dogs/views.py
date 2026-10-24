from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from . import services


def _int_param(request, name, default, lo, hi):
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


class _DogAPIView(APIView):
    """Protected by JWT only: a valid, unexpired access token is required."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def upstream_error(exc: services.UpstreamError):
        return Response({"detail": exc.detail, "code": "upstream_error"}, status=exc.status_code)


class BreedListView(_DogAPIView):
    """GET /api/dogs/breeds/?limit=10&page=0"""

    def get(self, request):
        limit = _int_param(request, "limit", 10, 1, 50)
        page = _int_param(request, "page", 0, 0, 1000)
        try:
            breeds = services.list_breeds(limit=limit, page=page)
        except services.UpstreamError as exc:
            return self.upstream_error(exc)
        return Response({"page": page, "limit": limit, "count": len(breeds), "results": breeds})


class BreedDetailView(_DogAPIView):
    """GET /api/dogs/breeds/<id>/"""

    def get(self, request, breed_id: int):
        try:
            breed = services.get_breed(breed_id)
        except services.UpstreamError as exc:
            return self.upstream_error(exc)
        return Response(breed)
