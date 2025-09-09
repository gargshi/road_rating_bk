import random, string
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from ratings.models import RoadRating, UserConversation
import logging
from utilities.cryptography import decode_chat_id
from urllib.parse import unquote
from ratings.models import TeleUser
logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
	#if not login
	if not request.user.is_authenticated and request.path != '/login/':
		return redirect('login')
	#fetch ratings from db and pass to template
	all_ratings = []  # Replace with actual query to fetch ratings
	user_conversations = []  # Replace with actual query to fetch user conversations
	login_user_id = request.session.get('chat_id')
	# user_conversations = UserConversation.objects.all().order_by('-updated_at')[:10]
	if login_user_id:
		user_conversations = UserConversation.objects.filter(fk_chat_id__chat_id=login_user_id).order_by('-updated_at')[:10]
		# all_ratings = RoadRating.objects.filter(fk_road_id__fk_chat_id__chat_id=login_user_id).order_by('-created_at')[:10]
		logger.info(f"Index view: fetched {len(user_conversations)} conversations and {len(all_ratings)} ratings for user {login_user_id}")
	# all_ratings = RoadRating.objects.all().order_by('-created_at')[:10]

	context = {"ratings": all_ratings, "user_conversations": user_conversations}
	return render(request, 'users_app/index.html', context)

def login_view(request):
	token = request.GET.get('uid')
	otp_from_url = request.GET.get("otp")
	if token:
		token = unquote(token)
		chat_id = decode_chat_id(token)
		if chat_id:
			request.session['chat_id'] = chat_id
			logger.info(f"Login view: decoded chat_id {chat_id} from token")
			if otp_from_url:
				request.session['otp_from_url'] = otp_from_url
				logger.info(f"Login view: OTP from URL: {otp_from_url}")
				return redirect("login_submit")
		else:
			logger.warning(f"Login view: failed to decode chat_id from token {token}")
	return render(request, 'users_app/login.html')

def login_submit(request):
	# user = authenticate(request, username=username, password=password)
	username = request.session.get('chat_id')
	if request.method == "POST":
		if not request.POST.get("password"):
			return render(request, 'users_app/login.html', {"error": "Missing OTP/Password. Please enter password manually."})
	password = (
		request.session.pop('otp_from_url', None)  # consume once if from URL
		or request.POST.get("password")            # manual login
	)
	if not password:
		return render(request, 'users_app/login.html', {"error": "Missing OTP/Password. Please enter password manually."})
	logger.info(f"Login view: OTP: {password}, username: {username}")
	try:
		logging_in_user = TeleUser.objects.get(chat_id=username)
	except TeleUser.DoesNotExist:
		return render(request, 'users_app/login.html', {"error": "User not found"})
		
	
	user = authenticate(request, username=username, password=password)
	logger.info(f"Login user: {user}, username: {username}, password: {password}")
	
	if user is not None:
		if logging_in_user.otp_active:
			return render(request, 'users_app/login.html', {"error": "Only one session allowed. Please contact support."})
		logging_in_user.otp_active=True
		logging_in_user.save()
		login(request, user)  # sets session
		return redirect('index')  # redirect by URL name
	else:
		return render(request, 'users_app/login.html', {"error": "Invalid credentials/OTP/URL"})	

def logout_view(request):
	if request.user.is_authenticated:
		logged_in_user = TeleUser.objects.get(chat_id=request.session.get('chat_id'))
		if logged_in_user:
			logged_in_user.otp_active=False
			logged_in_user.user.set_password(generate_random_otp())  # Invalidate the password
			logged_in_user.user.save()
			logged_in_user.save()
			logger.info(f"Logout view: Deactivated session for user {logged_in_user.chat_id}")
		logout(request)		
	request.session.flush()
	return redirect('thanks') # redirect to ending page.... telling the user to login again.... tbdd

def thanks_view(request):
	return render(request, 'users_app/thanks.html')

def generate_random_otp(k=6):
	"""Generate a random 6-digit OTP."""
	chars = string.ascii_letters + string.digits
	return ''.join(random.choices(chars, k=k))