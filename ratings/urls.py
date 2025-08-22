from django.urls import path
from .views import RoadRatingListCreate
from .views import webhook

urlpatterns = [
    path("ratings/", RoadRatingListCreate.as_view(), name="road-ratings"),
    path("telegram-webhook/", webhook, name="telegram_webhook"),
]