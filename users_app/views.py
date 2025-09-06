from django.shortcuts import render
from ratings.models import RoadRating, UserConversation

# Create your views here.
def index(request):
	#fetch ratings from db and pass to template
	all_ratings = []  # Replace with actual query to fetch ratings
	user_conversations = []  # Replace with actual query to fetch user conversations
	user_conversations = UserConversation.objects.all().order_by('-updated_at')[:10]

	# all_ratings = RoadRating.objects.all().order_by('-created_at')[:10]

	context = {"ratings": all_ratings, "user_conversations": user_conversations}
	return render(request, 'users_app/index.html', context)

def login_view(request):
	return render(request, 'users_app/login.html')

def login_submit(request):
	# Handle login form submission
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		# Authenticate user (this is a placeholder, implement actual authentication)
		if username == 'admin' and password == 'password':
			return render(request, 'users_app/index.html', {"message": "Login successful!"})
		else:
			return render(request, 'users_app/login.html', {"error": "Invalid credentials"})
	return render(request, 'users_app/login.html')