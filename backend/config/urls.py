from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from accounts.views import HealthView


def frontend_index(request):
    """Serve the built React app's index.html. Its JS/CSS files are served by WhiteNoise."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return HttpResponse(
            "<h1>API is running</h1><p>The frontend has not been built. "
            "Run <code>npm run build</code> in the frontend folder.</p>",
            status=200,
        )
    return HttpResponse(index.read_text(encoding="utf-8"))


urlpatterns = [
    path("", frontend_index, name="frontend"),
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/auth/", include("accounts.urls_jwt")),
    path("api/session/", include("accounts.urls_session")),
    path("api/dogs/", include("dogs.urls")),
]
