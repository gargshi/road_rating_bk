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
        location = data["message"].get("location", None)
        logger.info(f"Received message from {chat_id}: {text}, location: {location}")

        # Get latest conversation if any
        latest_conv = UserConversation.objects.filter(chat_id=chat_id).order_by("-updated_at").first()
        conv = latest_conv

        # ---------------- Commands ----------------
        if text == "/start":
            conv = UserConversation.objects.create(chat_id=chat_id, step="start")
            send_message(chat_id, "Hi! Welcome to the Road Rating Bot.")
            send_message(chat_id, "To rate a road, type /start \nTo cancel the current operation, type /cancel \nTo see your past ratings, type /past \n\nTo see this message again, type /help")                
            send_message(chat_id, "Enter the name of the road you want to rate?")
            conv.step = "ask_road"
            conv.save()
            return JsonResponse({"ok": True})

        if text == "/help":
            send_message(chat_id, "To rate a road, type /start \nTo cancel the current operation, type /cancel \nTo see your past ratings, type /past \n\nTo see this message again, type /help")
            return JsonResponse({"ok": True})

        if text == "/past":
            past_ratings = RoadRating.objects.filter(fk_road_id__chat_id=chat_id).order_by("-created_at")
            if past_ratings.exists():
                send_message(chat_id, "📝 Your past ratings:")
                for rating in past_ratings:
                    coords_text = ""
                    if rating.gps_coordinates and "," in rating.gps_coordinates:
                        lat, lon = rating.gps_coordinates.split(",")
                        maps_url = f"https://www.google.com/maps?q={lat.strip()},{lon.strip()}"
                        coords_text = f"[📍 View on Map]({maps_url})"
                    else:
                        coords_text = "—"
                    send_message(
                        chat_id,
                        f"Road: {rating.road_name}\n"
                        f"Rating: {rating.rating}\n"
                        f"Comment: {rating.comment or '—'}\n"
                        f"Coordinates: {coords_text or '—'}\n"
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
            conv.step = "ask_gps"
            conv.save()
            send_message(chat_id, "Thanks! Now please provide the GPS coordinates of the road:")
            

        elif conv.step == "ask_gps":
            if location:  # user sent attached location
                logger.info(f"Received location: {location}")
                lat = location["latitude"]
                lon = location["longitude"]
                conv.gps_coordinates = f"{lat}, {lon}"
            elif text:
                if "/skip" in text.lower():
                    conv.gps_coordinates = "Not provided"
                else:
                    conv.gps_coordinates = text
            else:
                send_message(chat_id, "⚠️ Please provide GPS coordinates (or /skip).")
                return JsonResponse({"ok": True})
            
            conv.step = "ask_comments"
            conv.save()
            send_message(chat_id, "Got it! Please add any comments:")

        elif conv.step == "ask_comments":
            conv.comment = text                   
            # Save feedback directly into DB
            logger.info("💾 Saving feedback to DB"
                        f" Road: {conv.road_name}, Rating: {conv.rating}, Comment: {conv.comment}, GPS: {conv.gps_coordinates}")
            feedback = RoadRating.objects.create(
                road_name=conv.road_name,
                rating=int(conv.rating),
                comment=conv.comment,
                gps_coordinates=conv.gps_coordinates  # Placeholder, as GPS not collected via Telegram
            )

            conv.fk_road_id = feedback
            conv.step = "complete"
            conv.save()

            send_message(chat_id, "✅ Feedback submitted. Thank you!")
            send_message(chat_id, "Want to add another? Please type /start")
        
        else:
            send_message(chat_id, "⚠️ Seems like a wrong command.\n ")
            send_message(chat_id, "To rate a road, type /start \n To cancel the current operation, type /cancel \n To see your past ratings, type /past \n\nTo see this message again, type /help")                

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error("❌ Error in webhook: %s", e, exc_info=True)
        return JsonResponse({"ok": False}, status=500)

user_sessions = {}
@csrf_exempt
def webhook_widgets(request):
    data = request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    if "text" in message:
        text = message["text"]

        # Start
        if text == "/start":
            keyboard = {
                "keyboard": [
                    [{"text": "➕ Rate a Road"}],
                    [{"text": "📝 View Past Ratings"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, "👋 Welcome to Road Rating Bot!", reply_markup=keyboard)

        # Start rating
        elif text == "➕ Rate a Road":
            user_sessions[chat_id] = {"step": "road_name"}
            send_message(chat_id, "📍 Please enter the road name:")

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
            send_message(chat_id, "⭐ Please rate the road (1–5):", reply_markup=keyboard)

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
            send_message(chat_id, "Would you like to add a comment?", reply_markup=keyboard)

        # Handle comment step
        elif user_sessions.get(chat_id, {}).get("step") == "comment":
            if text == "⏭ Skip":
                user_sessions[chat_id]["comment"] = None
            elif text == "📝 Add Comment":
                send_message(chat_id, "✍ Please type your comment:")
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
            send_message(chat_id, "📍 Please share the location:", reply_markup=keyboard)

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
            send_message(chat_id, "📍 Please share the location:", reply_markup=keyboard)

        # Skip location
        elif text == "⏭ Skip Location":
            save_rating(chat_id)
            del user_sessions[chat_id]

        # View past ratings
        elif text == "📝 View Past Ratings":
            past_ratings = RoadRating.objects.filter(fk_road_id__chat_id=chat_id).order_by("-created_at")
            if past_ratings.exists():
                send_message(chat_id, "📝 Your past ratings:")
                for rating in past_ratings:
                    maps_link = f"https://www.google.com/maps?q={rating.gps_coordinates}" if rating.gps_coordinates else "—"
                    send_message(
                        chat_id,
                        f"Road: {rating.road_name}\n"
                        f"Rating: {rating.rating}\n"
                        f"Comment: {rating.comment or '—'}\n"
                        f"Coordinates: {maps_link}\n"
                        f"Date: {rating.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    )
            else:
                send_message(chat_id, "ℹ️ You haven’t rated any roads yet.")

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
    RoadRating.objects.create(
        road_name=session.get("road_name"),
        rating=session.get("rating"),
        comment=session.get("comment"),
        gps_coordinates=session.get("gps_coordinates"),        
    )
    send_message(chat_id, "✅ Your road rating has been saved! Thank you 🙏")
