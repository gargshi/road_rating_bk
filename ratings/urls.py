from django.urls import path
from .views import RoadRatingListCreate

urlpatterns = [
    path("ratings/", RoadRatingListCreate.as_view(), name="road-ratings"),
]