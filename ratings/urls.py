from django.urls import path
from .views import webhook_widgets

urlpatterns = [
	path("telegram-webhook/", webhook_widgets, name="telegram_webhook"),
]