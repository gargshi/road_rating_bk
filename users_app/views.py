import random, string
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from ratings.models import RoadRating, UserConversation
import logging
from utilities.cryptography import decode_chat_id
from urllib.parse import unquote
from ratings.models import TeleUser
from django.core.paginator import Paginator
logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
	#if not login
	if not request.user.is_authenticated and request.path != '/login/':
		return redirect('login')
	#fetch ratings from db and pass to template
	all_ratings = []  # Replace with actual query to fetch ratings
	user_conversations = []  # Replace with actual query to fetch user conversations
	logger.info(f"Index view: Current session chat_id: {request.session.get('chat_id')}, Authenticated user: {request.user}")
	logger.info(f"session : {request.session.items()}")
	login_user_id = request.session.get('chat_id')
	# user_conversations = UserConversation.objects.all().order_by('-updated_at')[:10]
	logger.info(f"Index view: Current session chat_id: {login_user_id}, Authenticated user: {request.user}")
	if login_user_id:
		user_conversations = UserConversation.objects.filter(fk_chat_id__chat_id=login_user_id).order_by('-updated_at')[:10]
		paginator=Paginator(user_conversations,10)
		page_number=request.GET.get('page')
		page_obj=paginator.get_page(page_number)
		# all_ratings = RoadRating.objects.filter(fk_road_id__fk_chat_id__chat_id=login_user_id).order_by('-created_at')[:10]
		logger.info(f"Index view: fetched {len(user_conversations)} conversations and {len(all_ratings)} ratings for user {login_user_id}")
	else:
		logger.warning("Index view: No chat_id in session")
		logout(request)
	# all_ratings = RoadRating.objects.all().order_by('-created_at')[:10]

	context = {"ratings": all_ratings, "user_conversations": user_conversations, "page_obj": page_obj}
	return render(request, 'users_app/index.html', context)

def login_view(request):
	# If already logged in, redirect to index
	if request.user.is_authenticated:
		return redirect('index')
	token = request.GET.get('uid')
	if token:
		token = unquote(token)
		chat_id = decode_chat_id(token)
		if chat_id:
			request.session['chat_id'] = chat_id
			logger.info(f"Login view: decoded chat_id {chat_id} from token")
		else:
			logger.warning(f"Login view: failed to decode chat_id from token {token}")
	return render(request, 'users_app/login.html')

def login_submit(request):	
	if request.method == "POST":		
		username = request.session.get('chat_id')
		password = request.POST.get("password")
		otp_status=False
		if not password:
			return render(request, 'users_app/login.html', {"error": "Missing OTP/Password. Please enter password manually."})
		logger.info(f"Login view: OTP: {password}, username: {username}")			
		
		user = authenticate(request, username=username, password=password)
		logger.info(f"Login user: {user}, username: {username}, password: {password}")
		
		if user is not None:
			try:			
				logging_in_user = TeleUser.objects.get(chat_id=username)
				if logging_in_user.otp_active:
					logged_in_user = logging_in_user
					if logged_in_user:
						logged_in_user.otp_active=False
						logged_in_user.user.set_password(generate_random_otp())  # Invalidate the password
						logged_in_user.user.save()
						logged_in_user.save()
						logger.info(f"Logout view: Deactivated session for user {logged_in_user.chat_id}")		
						logout(request)		
						request.session.flush()
					return render(request, 'users_app/thanks.html', {"error": "Only one session allowed. Please generate new OTP"})
				logging_in_user.otp_active=True				
				logging_in_user.save()
			except TeleUser.DoesNotExist:
				return render(request, 'users_app/thanks.html', {"error": "User not found"})
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

def enable_login(chat_id, enable=True):
	# Enable OTP for the user
	logged_in_user = TeleUser.objects.get(chat_id=chat_id)
	if logged_in_user:
		if enable:
			logged_in_user.otp_active=True
			logger.info(f"Activated session for user {logged_in_user.chat_id}")
		else:		
			logged_in_user.otp_active=False
			logged_in_user.user.set_password(generate_random_otp())  # Invalidate the password
			logged_in_user.user.save()
			logger.info(f"Deactivated session for user {logged_in_user.chat_id}")
		logged_in_user.save()
	else:
		logger.warning(f"Enable login: User with chat_id {chat_id} not found")