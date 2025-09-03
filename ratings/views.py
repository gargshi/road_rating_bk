from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating, UserConversation, TeleUser, TeleUserStats
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


def send_message_text(chat_id, text):
    url = f"{TELEGRAM_URL}"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=payload)
    return response.json()

def send_message_markdown(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_URL}"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)
    # response = requests.post(url, json=payload)
    # return response.json()


def add_record(url, data):
    response = requests.post(url, json=data)
    return response.json()

user_sessions = {}
@csrf_exempt
def webhook_widgets(request):
    data = json.loads(request.body.decode("utf-8")) #request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    logger.info(f"Received message from {chat_id}: {message}")
    logger.info(f"Current session for {chat_id}: {user_sessions.get(chat_id)}")

    if user_sessions.get(chat_id) is None:
        user_sessions[chat_id] = {}

    if not chat_id:
        return JsonResponse({"ok": False})

    if "text" in message:
        text = message["text"]

        # Start
        if text in ["/start","✅ Yes, I want to rate more roads","START"]:            
            rate_road(chat_id)
        
        elif text == "❌ No, I don't want to rate more roads":
            send_message_markdown(chat_id, "👋 Thank you for using the Road Rating Bot! To start again, type /start",
                                  reply_markup={
                                    "keyboard": [
                                        [
                                            {"text": "START"},
                                        ]
                                    ],
                                    "resize_keyboard": True
                                }
                            )
            if chat_id in user_sessions:
                del user_sessions[chat_id]
            return JsonResponse({"ok": True})

        # Start rating
        elif text in ["➕ Rate a Road","rate_road"]:
            user_sessions[chat_id] = {"step": "road_name"}
            send_message_markdown(chat_id, "📍 Please enter the road name:")

        # Handle road name
        elif user_sessions.get(chat_id, {}).get("step") == "road_name":
            user_sessions[chat_id]["road_name"] = text
            user_sessions[chat_id]["step"] = "rating"
            keyboard = {
                "keyboard": [
                    [{"text": "⭐ 1"}, {"text": "⭐ 2"}],
                    [{"text": "⭐ 3"}, {"text": "⭐ 4"}, {"text": "⭐ 5"}]
                ],
                "resize_keyboard": True
            }
            send_message_markdown(chat_id, "⭐ Please rate the road (1–5):", reply_markup=keyboard)

        # Handle rating
        elif user_sessions.get(chat_id, {}).get("step") == "rating" and text.startswith("⭐"):
            rating_value = int(text.split()[1])
            user_sessions[chat_id]["rating"] = rating_value
            user_sessions[chat_id]["step"] = "comment"
            keyboard = {
                "keyboard": [
                    [{"text": "📝 Add Comment"}, {"text": "⏭ Skip"}]
                ],
                "resize_keyboard": True
            }
            send_message_markdown(chat_id, "Would you like to add a comment?", reply_markup=keyboard)

        # Handle comment step
        elif user_sessions.get(chat_id, {}).get("step") == "comment":
            if text == "⏭ Skip":
                user_sessions[chat_id]["comment"] = None
            elif text == "📝 Add Comment":
                send_message_markdown(chat_id, "✍ Please type your comment:")
                user_sessions[chat_id]["step"] = "comment_text"
                return JsonResponse({"ok": True})
            else:  # user typed comment
                user_sessions[chat_id]["comment"] = text

            # Next step → location
            user_sessions[chat_id]["step"] = "location"
            keyboard = {
                "keyboard": [
                    [{"text": "📍 Share Location", "request_location": True}],
                    [{"text": "⏭ Skip Location"}]
                ],
                "resize_keyboard": True
            }
            send_message_markdown(chat_id, "📍 Please share the location:", reply_markup=keyboard)

        # Handle comment text input
        elif user_sessions.get(chat_id, {}).get("step") == "comment_text":
            user_sessions[chat_id]["comment"] = text
            user_sessions[chat_id]["step"] = "location"
            keyboard = {
                "keyboard": [
                    [{"text": "📍 Share Location", "request_location": True}],
                    [{"text": "⏭ Skip Location"}]
                ],
                "resize_keyboard": True
            }
            send_message_markdown(chat_id, "📍 Please share the location:", reply_markup=keyboard)

        # Skip location
        elif text == "⏭ Skip Location":
            save_rating(chat_id)
            del user_sessions[chat_id]

        # View past ratings
        elif text in ["📝 View Past Ratings","past_ratings"]:
            past_ratings = RoadRating.objects.filter(fk_road_id__fk_chat_id__chat_id=chat_id).order_by("-created_at")
            if past_ratings.exists():
                send_message_markdown(chat_id, "📝 Your past ratings:")
                for rating in past_ratings:
                    maps_link = f"https://www.google.com/maps?q={rating.gps_coordinates}" if rating.gps_coordinates else "—"
                    send_message_markdown(
                        chat_id,
                        f"Road: {rating.road_name}\n"
                        f"Rating: {rating.rating}\n"
                        f"Comment: {rating.comment or '—'}\n"
                        f"Coordinates: {maps_link}\n"
                        f"Date: {rating.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    )
            else:
                send_message_markdown(chat_id, "ℹ️ You haven’t rated any roads yet.")
        
        else:
            send_message_markdown(chat_id, "⚠️ Unrecognized command. Please use the buttons to navigate. To start a new rating, type /start")            

    # Handle location
    elif "location" in message:
        lat = message["location"]["latitude"]
        lon = message["location"]["longitude"]
        gps = f"{lat},{lon}"
        user_sessions[chat_id]["gps_coordinates"] = gps
        save_rating(chat_id)
        del user_sessions[chat_id]        

    return JsonResponse({"ok": True})


def save_rating(chat_id):
    """Save rating to DB"""
    session = user_sessions.get(chat_id, {})
    if not session:
        send_message_markdown(chat_id, "⚠️ Session expired or invalid. Please start again with /start")
        return
    logger.info(f"💾 Saving rating for chat_id {chat_id}: {session}")
    feedback = RoadRating.objects.create(
        road_name=session.get("road_name"),
        rating=session.get("rating"),
        comment=session.get("comment"),
        gps_coordinates=session.get("gps_coordinates"),        
    )
    t_user=TeleUser.objects.get_or_create(chat_id=chat_id)
    UserConversation.objects.create(
        fk_chat_id=t_user[0],       
        fk_road_id=feedback,
    )
    send_message_markdown(chat_id, "✅ Your road rating has been saved! Thank you 🙏")
    want_to_continue(chat_id)

# def rate_road(chat_id):
#     keyboard = {
#         "keyboard": [
#             [{"text": "➕ Rate a Road"}],
#             [{"text": "📝 View Past Ratings"}],
#             [{"text": "📊 View Dashboard - (tbd)"}],
#             [{"text": "↩️ Exit"}]
#         ],
#         "resize_keyboard": True
#     }
#     send_message_markdown(chat_id, "👋 Welcome to Road Rating Bot!", reply_markup=keyboard)

def rate_road(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ Rate a Road", "callback_data": "rate_road"}],
            [{"text": "📝 View Past Ratings", "callback_data": "past_ratings"}],
            [{"text": "📊 View Dashboard - (tbd)", "callback_data": "dashboard"}],
            [{"text": "↩️ Exit - in", "callback_data": "exit"}]
        ],
        # "resize_keyboard": True
    }
    send_message_markdown(chat_id, "👋 Welcome to Road Rating Bot!", reply_markup=keyboard)

def want_to_continue(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "✅ Yes, I want to rate more roads"}],
            [{"text": "❌ No, I don't want to rate more roads"}]
        ],
        "resize_keyboard": True
    }
    send_message_markdown(chat_id, "👋 Do you want to rate more roads?", reply_markup=keyboard)