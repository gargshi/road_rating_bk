from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating, UserConversation
from .serializers import RoadRatingSerializer, UserConversationSerializer
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

class UserConversationListCreate(generics.ListCreateAPIView):
    queryset = UserConversation.objects.all().order_by("-updated_at")
    serializer_class = UserConversationSerializer

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_message(chat_id, text):
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

# @csrf_exempt
# @require_POST
# def webhook(request):
#     try:
#         body = request.body.decode("utf-8")
#         # logger.info("📩 Raw Telegram update: %s", body)

#         data = json.loads(body)
        
#         if "message" in data:
#             chat_id = str(data["message"]["chat"]["id"])
#             text = data["message"].get("text", "")
#             # conv, _ = UserConversation.objects.get_or_create(chat_id=chat_id) #edit in place in case of new rating
#             conv = UserConversation.objects.get_or_create(chat_id=chat_id) #get conversations
            
#             if text == "/start":
#                 send_message(chat_id, "Hi! Welcome to the Road Rating Bot.")
#                 send_message(chat_id, '''To rate a road, type /start \n
#                 To cancel the current operation, type /cancel \n 
#                 To see your past ratings, type /past \n\n
#                 To see this message again, type /help''')                
#                 conv.step = "start"
#                 conv.road_name = None
#                 conv.rating = None
#                 conv.comment = None
#                 conv.save()

#             if text == "/help":
#                 send_message(chat_id, '''To rate a road, type /start \n
#                 To cancel the current operation, type /cancel \n 
#                 To see your past ratings, type /past \n\n
#                 To see this message again, type /help''')
#                 # return JsonResponse({"ok": True})
            
#             if text == "/past":
#                 send_message(chat_id, "This feature is in progress. Stay tuned!")
#                 # send_message(chat_id, "Here are your past ratings:")
#                 #  Fetch and display past ratings from RoadRating model
#                 # past_ratings = RoadRating.objects.filter(user_id=chat_id).order_by("-created_at")
#                 # for rating in past_ratings:
#                 #     send_message(chat_id, f"Road: {rating.road_name}\nRating: {rating.rating}\nComment: {rating.comment}\nDate: {rating.created_at}\n\n")


#             if text == "/cancel":
#                 # send_message(chat_id, "Cancelled. To start over, type /start")
#                 latest_conv = UserConversation.objects.filter(chat_id=chat_id).order_by("-updated_at").first() # reset conversation
#                 if latest_conv:
#                     if latest_conv.step != "complete":
#                         latest_conv.delete()
#                     send_message(chat_id, "Cancelled. To start over, type /start")
#                 return JsonResponse({"ok": True})
            
#             if conv.step == "complete":
#                 send_message(chat_id, "Thanks! To start over, type /start")                
#                 return JsonResponse({"ok": True})
            
#             conv.step = conv.step if conv.step != "complete" else "start" # reset if previously complete


#             if conv.step == "start":                
#                 send_message(chat_id, "Enter the name of the road you want to rate?")
#                 conv.step = "ask_road"
#                 conv.save()
            
#             # elif conv.step == "check_incomplete_latest": 
#             #     latest_conv = UserConversation.objects.filter(chat_id=chat_id, step__in=["ask_road", "ask_rating", "ask_comments"]).order_by("-updated_at").first()
#             #     if latest_conv and latest_conv.step != "complete":
#             #         conv = latest_conv
#             #         send_message(chat_id, f"You have an incomplete rating for road: {conv.road_name if conv.road_name else 'N/A'}.")
#             #         send_message(chat_id, "Please continue where you left off.")
#             #         if conv.step == "ask_road":
#             #             send_message(chat_id, "Please enter the road name:")
#             #         elif conv.step == "ask_rating":
#             #             send_message(chat_id, "Please provide a rating (1-5):")
#             #         elif conv.step == "ask_comments":
#             #             send_message(chat_id, "Please add any comments:")
#             #         return JsonResponse({"ok": True})
#             #     else:
#             #         conv.step = "start"
#             #         conv.save()                   
            
#             elif conv.step == "ask_road": 
#                 conv.road_name = text
#                 conv.step = "ask_rating"
#                 conv.save()
#                 send_message(chat_id, "Thanks! Now give me a rating (1-5):")

#             elif conv.step == "ask_rating":
#                 conv.rating = text
#                 #validation
#                 if text not in ["1", "2", "3", "4", "5"]:
#                     send_message(chat_id, "Please provide a valid rating between 1 and 5.")
#                     return JsonResponse({"ok": True})
#                 conv.step = "ask_comments"
#                 conv.save()
#                 send_message(chat_id, "Got it! Please add any comments:")

#             elif conv.step == "ask_comments":
#                 conv.comment = text

#                 # Save feedback directly into DB
#                 feedback = RoadRating.objects.create(
#                     road_name=conv.road_name,
#                     rating=int(conv.rating),
#                     comment=conv.comment
#                 )

#                 conv.fk_road_id = feedback
#                 conv.step = "complete"  # reset for next round                
#                 conv.save()

#                 send_message(chat_id, "✅ Feedback submitted. Thank you!")
#                 send_message(chat_id, "Want to add another? Please type /start")

#             # else:
#             #     conv.step = "ask_road"
#             #     conv.save()
#             #     send_message(chat_id, "Hi! Please enter the road name:")

#             return JsonResponse({"ok": True})

#         return JsonResponse({"ok": False})             

        

#         # chat_id = data.get("message", {}).get("chat", {}).get("id")
#         # text = data.get("message", {}).get("text")

#         # logger.info("✅ Chat ID: %s, Text: %s", chat_id, text)

#         # Example reply (optional)
#         # add_record("http://127.0.0.1:8000/api/ratings/", {
#         #     "road_name": "From Telegram",
#         #     "rating": 5,
#         #     "comment": text
#         # })
#         # send_message(chat_id, f"You said: {text}", TELEGRAM_URL)

#        # return JsonResponse({"ok": True}) 
#     except Exception as e:
#         logger.error("❌ Error in webhook: %s", e, exc_info=True)
#         return JsonResponse({"ok": False}, status=500)

@csrf_exempt
@require_POST
def webhook(request):
    try:
        body = request.body.decode("utf-8")
        data = json.loads(body)
        
        if "message" not in data:
            return JsonResponse({"ok": False})

        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"].get("text", "").strip()

        # Get latest conversation if any
        latest_conv = UserConversation.objects.filter(chat_id=chat_id).order_by("-updated_at").first()
        conv = latest_conv

        # ---------------- Commands ----------------
        if text == "/start":
            conv = UserConversation.objects.create(chat_id=chat_id, step="start")
            send_message(chat_id, "Hi! Welcome to the Road Rating Bot.")
            send_message(chat_id, '''To rate a road, type /start \n
            To cancel the current operation, type /cancel \n 
            To see your past ratings, type /past \n\n
            To see this message again, type /help''')                
            send_message(chat_id, "Enter the name of the road you want to rate?")
            conv.step = "ask_road"
            conv.save()
            return JsonResponse({"ok": True})

        if text == "/help":
            send_message(chat_id, '''To rate a road, type /start \n
            To cancel the current operation, type /cancel \n 
            To see your past ratings, type /past \n\n
            To see this message again, type /help''')
            return JsonResponse({"ok": True})

        if text == "/past":
            past_ratings = RoadRating.objects.filter(fk_road_id__chat_id=chat_id).order_by("-created_at")
            if past_ratings.exists():
                send_message(chat_id, "📝 Your past ratings:")
                for rating in past_ratings:
                    send_message(
                        chat_id,
                        f"Road: {rating.road_name}\n"
                        f"Rating: {rating.rating}\n"
                        f"Comment: {rating.comment or '—'}\n"
                        f"Date: {rating.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    )
            else:
                send_message(chat_id, "ℹ️ You haven’t rated any roads yet.")
            return JsonResponse({"ok": True})

        if text == "/cancel":
            if latest_conv and latest_conv.step != "complete":
                latest_conv.delete()
            send_message(chat_id, "Cancelled. To start over, type /start")
            return JsonResponse({"ok": True})

        if conv is None:
            # No active conversation, ask them to start
            send_message(chat_id, "Please type /start to begin rating a road.")
            return JsonResponse({"ok": True})

        if conv.step == "complete":
            send_message(chat_id, "Thanks! To start a new rating, type /start")                
            return JsonResponse({"ok": True})

        # ---------------- Rating Flow ----------------
        if conv.step == "ask_road":
            conv.road_name = text
            conv.step = "ask_rating"
            conv.save()
            send_message(chat_id, "Thanks! Now give me a rating (1-5):")

        elif conv.step == "ask_rating":
            if text not in ["1", "2", "3", "4", "5"]:
                send_message(chat_id, "⚠️ Please provide a valid rating between 1 and 5.")
                return JsonResponse({"ok": True})
            conv.rating = text
            conv.step = "ask_comments"
            conv.save()
            send_message(chat_id, "Got it! Please add any comments:")

        elif conv.step == "ask_comments":
            conv.comment = text

            # Save feedback directly into DB
            feedback = RoadRating.objects.create(
                road_name=conv.road_name,
                rating=int(conv.rating),
                comment=conv.comment
            )

            conv.fk_road_id = feedback
            conv.step = "complete"
            conv.save()

            send_message(chat_id, "✅ Feedback submitted. Thank you!")
            send_message(chat_id, "Want to add another? Please type /start")

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error("❌ Error in webhook: %s", e, exc_info=True)
        return JsonResponse({"ok": False}, status=500)