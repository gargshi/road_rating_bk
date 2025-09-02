from django.urls import path
from .views import RoadRatingListCreate,UserConversationListCreate
from .views import webhook, webhook_widgets

urlpatterns = [
    path("ratings/", RoadRatingListCreate.as_view(), name="road-ratings"),
	path("conversations/", UserConversationListCreate.as_view(), name="user-conversations"),
	path("telegram-webhook/", webhook_widgets, name="telegram_webhook"),
]