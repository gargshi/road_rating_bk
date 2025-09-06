from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating, UserConversation, TeleUser, TeleUserStats
from .serializers import RoadRatingSerializer, UserConversationSerializer
from django.http import JsonResponse
import requests, json
import os
import re
from django.views.decorators.csrf import csrf_exempt
import logging
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
logger = logging.getLogger(__name__)

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer

class UserConversationListCreate(generics.ListCreateAPIView):
    queryset = UserConversation.objects.all().order_by("-updated_at")
    serializer_class = UserConversationSerializer

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
COMMANDS = {
        "/start": "start",
        "START": "start",
        "✅ Yes, I want to rate more roads": "start",
        "❌ No, I don't want to rate more roads": "stop",
        "➕ Rate a Road": "rate",
        "📝 View Past Ratings": "past_ratings",
        "📊 View Dashboard - (tbd)": "dashboard",
        "↩️ Exit": "exit",
        "⏭ Skip": "skip",
        "📝 Add Comment":"add_comment",
        "⏭ Skip Location": "skip_location",
        "📍 Share Location": "share_location",        
    }

# def send_message_text(chat_id, text):
#     url = f"{TELEGRAM_URL}"
#     payload = {
#         "chat_id": chat_id,
#         "text": text
#     }
#     response = requests.post(url, json=payload)
#     return response.json()

def send_message_markdown(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_URL}"
    # text=COMMANDS.get(text,text)  # map to command if exists
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
        logger.info(f"Received text: {text}")
        text=COMMANDS.get(text,text)
        logger.info(f"Processed text command: {text}")

        # Start
        if text in ["start"]:
            t_user=create_teleuser_if_not_exists(chat_id=chat_id)
            user_sessions[chat_id] = {"tuser": t_user}                
            rate_road(chat_id)
        
        elif text in ["stop","exit"]:
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
        elif text in ["rate"]:
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
            if text == "skip":
                user_sessions[chat_id]["comment"] = None
            elif text == "add_comment":
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
        elif text == "skip_location":
            save_rating(chat_id)
            del user_sessions[chat_id]

        # View past ratings
        elif text in ["past_ratings"]:
            past_ratings = RoadRating.objects.filter(fk_road_id__fk_chat_id__chat_id=chat_id).order_by("-created_at")
            logger.info(f"Found {past_ratings.count()} past ratings for chat_id {chat_id}")
            if past_ratings.exists():
                send_message_markdown(chat_id, "📝 Your past ratings:")
                for rating in past_ratings:
                    logger.info(f"Found rating: {rating}")
                    maps_link = f"https://www.google.com/maps?q={rating.gps_coordinates}" if rating.gps_coordinates else "—"
                    send_message_markdown(
                        chat_id,
                        f"Road: {escape_markdown(rating.road_name)}\n"
                        f"Rating: {rating.rating}\n"
                        f"Comment: {escape_markdown(rating.comment) or '—'}\n"
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
    # t_user=TeleUser.objects.get_or_create(chat_id=chat_id)
    # t_user=create_teleuser_if_not_exists(chat_id=chat_id)
    t_user=session.get("tuser") or create_teleuser_if_not_exists(chat_id=chat_id)
    UserConversation.objects.create(
        fk_chat_id=t_user,       
        fk_road_id=feedback,
    )
    send_message_markdown(chat_id, "✅ Your road rating has been saved! Thank you 🙏")
    want_to_continue(chat_id)

def rate_road(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "➕ Rate a Road"}],
            [{"text": "📝 View Past Ratings"}],
            [{"text": "📊 View Dashboard - (tbd)"}],
            [{"text": "↩️ Exit"}]
        ],
        "resize_keyboard": True
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

def escape_markdown(text: str) -> str:
    if not text:  # catches None, empty string, etc.
        return "---"
    escape_chars = r'[_*[\]()~`>#+\-=|{}.!]'
    return re.sub(escape_chars, r'\\\g<0>', text)

def create_teleuser_if_not_exists(chat_id, first_name=None, last_name=None, username=None, language_code=None, is_bot=False):
    # always map to Django User (using chat_id as username if no explicit username provided)
    user_username = str(chat_id)

    user, user_created = User.objects.get_or_create(username=user_username)
    if user_created:
        user.set_password("123456")  # hash properly the password... password is currently hardcoded
        user.save()

    tele_user, created = TeleUser.objects.get_or_create(
        chat_id=str(chat_id),
        defaults={
            "user": user,  # link to Django User
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_bot": is_bot,
        },
    )
    # Ensure the TeleUser is linked to the User
    if tele_user.user is None and user:
        tele_user.user = user
        logger.info(f"Linking TeleUser {tele_user.chat_id} to User {user.username}")
        tele_user.save()
        logger.info(f"Linked TeleUser {tele_user.chat_id} to User {user.username}")

    if created or user_created:
        logger.info(f"Created new TeleUser: {tele_user} (linked to User: {user.username})")

    return tele_user