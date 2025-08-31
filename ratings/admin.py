from django.contrib import admin
from .models import RoadRating, UserConversation
# Register your models here.
class RoadRatingAdmin(admin.ModelAdmin):
	list_display = ('road_name', 'rating', 'comment', 'created_at')
	search_fields = ('road_name', 'comment')
	list_filter = ('rating', 'created_at')

class UserConversationAdmin(admin.ModelAdmin):
	list_display = ('chat_id', 'step', 'fk_road_id', 'updated_at')
	search_fields = ('chat_id',)
	list_filter = ('step', 'updated_at')

admin.site.register(RoadRating, RoadRatingAdmin)
admin.site.register(UserConversation, UserConversationAdmin)