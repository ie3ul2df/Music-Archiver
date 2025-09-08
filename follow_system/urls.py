from django.urls import path
from . import views

app_name = "follow"

urlpatterns = [
    path("u/<str:username>/toggle/", views.toggle_follow, name="toggle"),
    path("u/<str:username>/follow/", views.follow_user, name="follow"),
    path("u/<str:username>/unfollow/", views.unfollow_user, name="unfollow"),

    # optional lists
    path("u/<str:username>/followers/", views.followers_list, name="followers"),
    path("u/<str:username>/following/", views.following_list, name="following"),
]
