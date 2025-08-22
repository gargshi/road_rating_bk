from django.shortcuts import render
from rest_framework import generics
from .models import RoadRating
from .serializers import RoadRatingSerializer

class RoadRatingListCreate(generics.ListCreateAPIView):
	queryset = RoadRating.objects.all().order_by("-created_at")
	serializer_class = RoadRatingSerializer