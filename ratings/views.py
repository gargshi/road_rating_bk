from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating
from .serializers import RoadRatingSerializer
from django.http import JsonResponse
import requests, json
import os
from django.views.decorators.csrf import csrf_exempt
import logging
logger = logging.getLogger(__name__)

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# @csrf_exempt
# def webhook(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         logger.info(f"Incoming update: {data}")
#         chat_id = data["message"]["chat"]["id"]
#         text = data["message"].get("text", "")
#         print(f"Received message: {text} from chat_id: {chat_id}")

#         # Reply back
#         reply = {"chat_id": chat_id, "text": f"You said: {text}"}
#         r=requests.post(TELEGRAM_URL, json=reply)
#         logger.info(f"Telegram reply status: {r.status_code}, {r.text}")
#         return JsonResponse({"status": "ok"})
#     return JsonResponse({"error": "invalid"}, status=400)

@csrf_exempt
def webhook(request):
    if request.method == "POST":
        try:
            body_unicode = request.body.decode("utf-8")
            if not body_unicode:  # 🛡 prevent empty body crash
                return JsonResponse({"error": "empty body"}, status=400)

            data = json.loads(body_unicode)
            print("Incoming update:", data)  # log raw payload

            # Handle only messages safely
            if "message" in data:
                chat_id = data["message"]["chat"]["id"]
                text = data["message"].get("text", "")

                reply = {"chat_id": chat_id, "text": f"You said: {text}"}
                r = requests.post(TELEGRAM_URL, json=reply)
                print("Telegram API reply:", r.status_code, r.text)

            return JsonResponse({"status": "ok"})
        except json.JSONDecodeError as e:
            print("JSON parse error:", e, " Raw body:", request.body)
            return JsonResponse({"error": "invalid JSON"}, status=400)
    return JsonResponse({"error": "invalid method"}, status=405)