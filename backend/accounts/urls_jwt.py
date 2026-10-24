from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import DemoExpiredTokenView, LogoutView, MeView, ThrottledLoginView

urlpatterns = [
    path("login/", ThrottledLoginView.as_view(), name="jwt-login"),
    path("refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    path("logout/", LogoutView.as_view(), name="jwt-logout"),
    path("me/", MeView.as_view(), name="jwt-me"),
    path("demo/expired-token/", DemoExpiredTokenView.as_view(), name="jwt-demo-expired"),
]
