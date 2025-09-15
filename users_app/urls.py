from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("login/submit/", views.login_submit, name="login_submit"),
    path("logout/", views.logout_view, name="logout"),
	path("thanks/", views.thanks_view, name="thanks"),  # New path for thanks view
	path("get-presigned-urls/<int:road_id>/", views.get_presigned_urls, name="get_presigned_urls"),
]