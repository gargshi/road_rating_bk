from django.shortcuts import render
from ratings.models import RoadRating

# Create your views here.
def index(request):
	#fetch ratings from db and pass to template
	all_ratings = []  # Replace with actual query to fetch ratings
	all_ratings = RoadRating.objects.all().order_by('-created_at')[:10]
	context = {"ratings": all_ratings}
	return render(request, 'users_app/index.html', context)