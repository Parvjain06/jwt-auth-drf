from django.urls import path

from .views import BreedDetailView, BreedListView

urlpatterns = [
    path("breeds/", BreedListView.as_view(), name="dog-breeds"),
    path("breeds/<int:breed_id>/", BreedDetailView.as_view(), name="dog-breed-detail"),
]
