from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating, UserConversation
from .serializers import RoadRatingSerializer
from django.http import JsonResponse
import requests, json
import os
from django.views.decorators.csrf import csrf_exempt
import logging
from django.views.decorators.http import require_POST
logger = logging.getLogger(__name__)

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer


TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
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


def send_message(chat_id, text, TELEGRAM_URL):
    url = f"{TELEGRAM_URL}"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=payload)
    return response.json()

def add_record(url, data):
    response = requests.post(url, json=data)
    return response.json()

@csrf_exempt
@require_POST
def webhook(request):
    try:
        body = request.body.decode("utf-8")
        # logger.info("📩 Raw Telegram update: %s", body)

        data = json.loads(body)
        
        if "message" in data:
            chat_id = str(data["message"]["chat"]["id"])
            text = data["message"].get("text", "")

            conv, _ = UserConversation.objects.get_or_create(chat_id=chat_id)

            if conv.step == "ask_road":
                conv.road = text
                conv.step = "ask_rating"
                conv.save()
                send_message(chat_id, "Thanks! Now give me a rating (1-5):")

            elif conv.step == "ask_rating":
                conv.rating = text
                conv.step = "ask_comments"
                conv.save()
                send_message(chat_id, "Got it! Please add any comments:")

            elif conv.step == "ask_comments":
                conv.comments = text

                # Save feedback directly into DB
                feedback = RoadRating.objects.create(
                    road_name=conv.road,
                    rating=int(conv.rating),
                    comments=conv.comments
                )

                conv.fk_road_id = feedback
                conv.step = "ask_road"  # reset for next round
                conv.road = None
                conv.rating = None
                conv.comments = None
                conv.save()

                send_message(chat_id, "✅ Feedback submitted. Thank you! Want to add another? Please enter the road name:")

            else:
                conv.step = "ask_road"
                conv.save()
                send_message(chat_id, "Hi! Please enter the road name:")

            return JsonResponse({"ok": True})

        return JsonResponse({"ok": False})             

        

        # chat_id = data.get("message", {}).get("chat", {}).get("id")
        # text = data.get("message", {}).get("text")

        # logger.info("✅ Chat ID: %s, Text: %s", chat_id, text)

        # Example reply (optional)
        # add_record("http://127.0.0.1:8000/api/ratings/", {
        #     "road_name": "From Telegram",
        #     "rating": 5,
        #     "comment": text
        # })
        # send_message(chat_id, f"You said: {text}", TELEGRAM_URL)

       # return JsonResponse({"ok": True}) 
    except Exception as e:
        logger.error("❌ Error in webhook: %s", e, exc_info=True)
        return JsonResponse({"ok": False}, status=500)