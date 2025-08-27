from django.db import models

class RoadRating(models.Model):
    road_name = models.CharField(max_length=255)
    rating = models.IntegerField()  # 1–5 stars
    comment = models.TextField(blank=True, null=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.road_name} - {self.rating}⭐"

class UserConversation(models.Model):
    chat_id = models.CharField(max_length=50)
    step = models.CharField(max_length=20, default="start")

    # Temporary storage during conversation
    road_name = models.TextField(null=True, blank=True)
    rating = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, null=True)

    # Link to final feedback (once submitted)
    fk_road_id = models.ForeignKey(
        RoadRating, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="fk_road_id"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.chat_id} - {self.step}"