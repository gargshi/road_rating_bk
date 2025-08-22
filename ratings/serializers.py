from rest_framework import serializers
from .models import RoadRating

class RoadRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadRating
        fields = "__all__"