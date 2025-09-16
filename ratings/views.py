import mimetypes
import boto3
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics
from .models import RoadMedia, RoadRating, UserConversation, TeleUser, TeleUserStats
from .serializers import RoadRatingSerializer, UserConversationSerializer
from django.http import JsonResponse
import requests, json
import os
import re
from django.views.decorators.csrf import csrf_exempt
import logging
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
import random
from utilities.cryptography import encode_chat_id
from urllib.parse import quote
from users_app.views import enable_login
logger = logging.getLogger(__name__)

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer

class UserConversationListCreate(generics.ListCreateAPIView):
    queryset = UserConversation.objects.all().order_by("-updated_at")
    serializer_class = UserConversationSerializer

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
LOGIN_URL = "https://road-rating-bk.onrender.com/"
COMMANDS = {
        "/start": "start",
        "START": "start",
        "/exit": "exit",
        "✅ Yes, I want to rate more roads": "start",
        "❌ No, I don't want to rate more roads": "stop",
        "➕ Rate a Road": "rate",
        "📝 View Past Ratings": "past_ratings",
        "📊 View Dashboard": "dashboard",
        "↩️ Exit": "exit",
        "⏭ Skip": "skip",
        "📝 Add Comment":"add_comment",
        "⏭ Skip Location": "skip_location",
        "📍 Share Location": "share_location",
        "📎 Add Media": "add_media",
        "⏭ Skip Media": "skip_media",        
    }

def send_message_markdown(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    url = f"{TELEGRAM_URL}"
    # text=COMMANDS.get(text,text)  # map to command if exists
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)
    # response = requests.post(url, json=payload)
    # return response.json()


# def add_record(url, data):
#     response = requests.post(url, json=data)
#     return response.json()

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
    
    # Handle media (photo, video, document)
    if "photo" in message or "video" in message or "document" in message:
        session = user_sessions.get(chat_id, {})
        road_id = session.get("road_id")
        if not road_id:
            send_message_markdown(chat_id, "⚠️ Please start a rating session first by typing /start and following the prompts.")
            return JsonResponse({"ok": False})
        if handle_media_upload(message, chat_id, session, road_id):
            send_message_markdown(chat_id, f"📎 Media added")
            add_more_media_prompt(chat_id)
        else:
            send_message_markdown(chat_id, "⚠️ Could not upload media. Please try again from dashboard. Thanks.")
        # save_rating(chat_id)
        # return JsonResponse({"ok": True})
    

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
            exiting_program(chat_id)
            return JsonResponse({"ok": True})

        # Start rating
        elif text in ["rate"]:
            user_sessions[chat_id] = {"step": "road_name"}
            keyboard = {
                    "keyboard": [
                        [{"text": "↩️ Exit"}]
                    ],
                    "resize_keyboard": True,
                }
            send_message_markdown(chat_id, "Please enter the road name:",reply_markup=keyboard)
        
        #go to dashboard - tbd
        elif text in ["dashboard"]:
            user_sessions[chat_id] = {"step": "dashboard"}
            # enable_login(chat_id, enable=False)
            show_dashboard_otp_logic(chat_id)            

        # Handle road name
        elif user_sessions.get(chat_id, {}).get("step") == "road_name":
            user_sessions[chat_id]["road_name"] = text
            user_sessions[chat_id]["step"] = "rating"
            add_rating_prompt(chat_id)

        # Handle rating
        elif user_sessions.get(chat_id, {}).get("step") == "rating" and text.startswith("⭐"):
            rating_value = int(text.split()[1])
            user_sessions[chat_id]["rating"] = rating_value
            user_sessions[chat_id]["step"] = "comment"
            add_comment_prompt(chat_id)

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
            add_location_prompt(chat_id)

        # Handle comment text input
        elif user_sessions.get(chat_id, {}).get("step") == "comment_text":
            user_sessions[chat_id]["comment"] = text
            user_sessions[chat_id]["step"] = "location"
            add_location_prompt(chat_id)

        # Skip location
        elif text == "skip_location":
            user_sessions[chat_id]["gps_coordinates"] = None
            user_sessions[chat_id]["step"] = "media"
            create_road_rating_and_conversation(chat_id)         
            add_media_prompt(chat_id)
        
        elif text == "add_media":
            keyboard = {
                "keyboard": [                    
                    [{"text": "⏭ Skip Media"}]
                ],
                "resize_keyboard": True
            }
            send_message_markdown(chat_id, "📎 Please upload any supporting media (photos, videos) you want to attach to this rating.", reply_markup=keyboard)
        
        elif text in "skip_media":
            save_rating(chat_id)
            del user_sessions[chat_id]


        # View past ratings
        elif text in ["past_ratings"]:
            past_rating(chat_id)
        
        else:
            send_message_markdown(chat_id, "⚠️ Unrecognized command. Please use the buttons to navigate. To start a new rating, type /start")            

    # Handle location
    elif "location" in message:
        lat = message["location"]["latitude"]
        lon = message["location"]["longitude"]
        gps = f"{lat},{lon}"
        user_sessions[chat_id]["gps_coordinates"] = gps
        user_sessions[chat_id]["step"] = "media"
        create_road_rating_and_conversation(chat_id)
        add_media_prompt(chat_id)
        # save_rating(chat_id)
        # del user_sessions[chat_id]
    
    else:
        send_message_markdown(chat_id, "⚠️ Unrecognized input. Please use the buttons to navigate. To start a new rating, type /start")

    return JsonResponse({"ok": True})

def exiting_program(chat_id):
    keyboard = {"keyboard": 
                        [
                            [
                                {"text": "START"},
                            ]
                        ],
                        "resize_keyboard": True
                    }
    send_message_markdown(chat_id, "👋 Thank you for using the Road Rating Bot! To start again, type /start", reply_markup=keyboard)
    if chat_id in user_sessions:
        del user_sessions[chat_id]

def add_more_media_prompt(chat_id):
    keyboard = {
                "keyboard": [
                    [{"text": "📎 Add Media"},{"text": "⏭ Skip Media"}],                    
                    [{"text": "↩️ Exit"}]
                ],
                "resize_keyboard": True
            }
    send_message_markdown(chat_id, "Would you like to add any more supporting media (photos, videos)?", reply_markup=keyboard)

def show_dashboard_otp_logic(chat_id):
    secret_otp=random.randint(100000,999999)
    user_sessions[chat_id]["otp"]=secret_otp
    token = encode_chat_id(str(chat_id))
    safe_token = quote(token, safe="")
    url = f"https://road-rating-bk.onrender.com/login?uid={safe_token}"            
    logger.info(f"Generated OTP {secret_otp} and token {token} for chat_id {chat_id}")         
    if set_otp_for_user(chat_id,secret_otp):
        logger.info(f"sending message to chat_id {chat_id} with token {token} and otp {secret_otp}")
        send_message_markdown(chat_id, f"To access the dashboard, go to {url} \n Password: {secret_otp}", parse_mode="HTML")                
    else:
        send_message_markdown(chat_id, "⚠️ Unable to set OTP for your user. Please contact support.")

def add_rating_prompt(chat_id):
    keyboard = {
                "keyboard": [
                    [{"text": "⭐ 1"}, {"text": "⭐ 2"}],
                    [{"text": "⭐ 3"}, {"text": "⭐ 4"}, {"text": "⭐ 5"}]
                ],
                "resize_keyboard": True
            }
    send_message_markdown(chat_id, "⭐ Please rate the road (1–5):", reply_markup=keyboard)

def add_comment_prompt(chat_id):
    keyboard = {
                "keyboard": [
                    [{"text": "📝 Add Comment"}, {"text": "⏭ Skip"}],
                    [{"text": "↩️ Exit"}]
                ],
                "resize_keyboard": True
            }
    send_message_markdown(chat_id, "Would you like to add a comment?", reply_markup=keyboard)

def add_location_prompt(chat_id):
    keyboard = {
                "keyboard": [
                    [{"text": "📍 Share Location", "request_location": True},{"text": "⏭ Skip Location"}],                    
                    [{"text": "↩️ Exit"}]
                ],
                "resize_keyboard": True
            }
    send_message_markdown(chat_id, "📍 Please share the location:", reply_markup=keyboard)

def past_rating(chat_id):
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


def create_road_rating_and_conversation(chat_id):
    """Create road rating and conversation"""
    session = user_sessions.get(chat_id, {})
    if not session:
        send_message_markdown(chat_id, "⚠️ Session expired or invalid. Please start again with /start")
        return
    logger.info(f"💾 Creating road rating and conversation for chat_id {chat_id}: {session}")
    feedback = RoadRating.objects.create(
        road_name=session.get("road_name"),
        rating=session.get("rating"),
        comment=session.get("comment"),
        gps_coordinates=session.get("gps_coordinates"),        
    )    
    t_user=session.get("tuser") or create_teleuser_if_not_exists(chat_id=chat_id)
    UserConversation.objects.create(
        fk_chat_id=t_user,       
        fk_road_id=feedback,
    )
    logger.info(f"Created RoadRating {feedback.id} and UserConversation for chat_id {chat_id}")
    session["road_id"]=feedback.id
    # add_media_prompt(chat_id)
    
def save_rating(chat_id):
    send_message_markdown(chat_id, "✅ Your road rating has been saved! Thank you 🙏")
    want_to_continue(chat_id)

def add_media_prompt(chat_id):
    keyboard = {
                "keyboard": [
                    [{"text": "📎 Add Media"}],   
                    [{"text": "⏭ Skip Media"}],
                    [{"text": "↩️ Exit"}]
                ],
                "resize_keyboard": True
            }
    send_message_markdown(chat_id, "Would you like to add any supporting media (photos, videos)?", reply_markup=keyboard)

def set_otp_for_user(chat_id,otp):
    try:
        session = user_sessions.get(chat_id, {})
        t_user=session.get("tuser") or TeleUser.objects.get(chat_id=chat_id)
        if t_user and t_user.user:
            t_user.user.set_password(str(otp))
            # t_user.otp_active=True
            # t_user.save()
            t_user.user.save()
            logger.info(f"Set OTP for user {t_user.user.username}")
            return True
    except TeleUser.DoesNotExist:
        logger.error(f"TeleUser with chat_id {chat_id} does not exist")
    return False

def rate_road(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "➕ Rate a Road"}],
            [{"text": "📝 View Past Ratings"}],
            [{"text": "📊 View Dashboard"}],            
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
    session = user_sessions.get(chat_id, {})

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


def get_presigned_url(request, filename):
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": f"user_uploads/{filename}"},
        ExpiresIn=300  # 5 mins
    )
    return JsonResponse({
        "upload_url": url,
        "file_url": f"https://{bucket}.s3.amazonaws.com/user_uploads/{filename}"
    })



def handle_media_upload(message, chat_id, session, road_id):
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        file_id = None
        orig_filename = None
        content_type = None
        media_type = "doc"

        if "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            orig_filename = f"{file_id}.jpg"
            content_type = "image/jpeg"
            media_type = "photo"
        elif "video" in message:
            file_id = message["video"]["file_id"]
            orig_filename = f"{file_id}.mp4"
            content_type = message["video"].get("mime_type", "video/mp4")
            media_type = "video"
        elif "document" in message:
            file_id = message["document"]["file_id"]
            orig_filename = message["document"].get("file_name") or f"{file_id}"
            content_type = message["document"].get("mime_type") or mimetypes.guess_type(orig_filename)[0] or "application/octet-stream"
            media_type = "doc"

        # Get Telegram file URL
        getfile_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}")
        getfile_res.raise_for_status()
        file_path = getfile_res.json()["result"]["file_path"]
        tg_file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

        # Download from Telegram
        r = requests.get(tg_file_url, stream=True)
        r.raise_for_status()

        road = RoadRating.objects.get(id=road_id)
        road_media = RoadMedia.objects.create(fk_road=road)

        # Generate uuid + extension
        ext = os.path.splitext(orig_filename)[1] or mimetypes.guess_extension(content_type) or ""
        
        # s3_key = f"user_uploads/{session.get('road_id','pending')}/{unique_id}{ext}"
        s3_key = f"road_media/{road_media.id}.jpg"

        # Upload to S3
        s3.upload_fileobj(
            r.raw,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )

        # Save media record
        road_media.file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        road_media.media_type = media_type
        road_media.save()
        session['road_media_id']=road_media.id
        logger.info(f"Saved RoadMedia {road_media.id} for RoadRating {road_id}")
        return True
    except Exception as e:
        logger.exception("Media upload failed")
        return False