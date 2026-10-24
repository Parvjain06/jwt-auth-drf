from django.urls import path

from .views import SessionLoginView, SessionLogoutView, SessionMeView

urlpatterns = [
    path("login/", SessionLoginView.as_view(), name="session-login"),
    path("logout/", SessionLogoutView.as_view(), name="session-logout"),
    path("me/", SessionMeView.as_view(), name="session-me"),
]
