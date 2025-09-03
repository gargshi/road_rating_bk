from django.db import models

class TeleUser(models.Model):
    chat_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    # username = models.CharField(max_length=100, blank=True, null=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    is_bot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_interaction_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"({self.chat_id})"

class TeleUserStats(models.Model):
    user = models.OneToOneField(TeleUser, on_delete=models.CASCADE, related_name="stats")
    total_ratings = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    total_rating_points = models.IntegerField(default=0)
    last_rating_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Stats for {self.user.chat_id}"

class RoadRating(models.Model):
    road_name = models.CharField(max_length=255, null=True, blank=True)
    rating = models.IntegerField(blank=True, null=True)  # 1–5 stars
    comment = models.TextField(blank=True, null=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.road_name} - {self.rating}⭐"

class UserConversation(models.Model):
    # chat_id = models.CharField(max_length=50)    
    fk_chat_id = models.ForeignKey(
        TeleUser, on_delete=models.CASCADE,
        related_name="fk_chat_id",
        null=True, blank=True
    )
    # state = models.CharField(max_length=50, default="START")
    # Link to final feedback (once submitted)
    fk_road_id = models.ForeignKey(
        RoadRating, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="fk_road_id"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fk_chat_id} - {self.fk_road_id}"