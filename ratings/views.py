from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating
from .serializers import RoadRatingSerializer
from django.http import JsonResponse
import requests, json
import os
from django.views.decorators.csrf import csrf_exempt

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

@csrf_exempt
def webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Reply back
        reply = {"chat_id": chat_id, "text": f"You said: {text}"}
        requests.post(TELEGRAM_URL, json=reply)

        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "invalid"}, status=400)