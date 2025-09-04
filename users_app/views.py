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