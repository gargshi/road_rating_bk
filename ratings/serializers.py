from rest_framework import serializers
from .models import RoadRating, UserConversation

class RoadRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadRating
        fields = "__all__"

class UserConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConversation
        fields = "__all__"