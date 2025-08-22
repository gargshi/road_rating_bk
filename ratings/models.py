from django.db import models

class RoadRating(models.Model):
    road_name = models.CharField(max_length=255)
    rating = models.IntegerField()  # 1–5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.road_name} - {self.rating}⭐"