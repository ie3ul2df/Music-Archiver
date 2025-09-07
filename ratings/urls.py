from django.urls import path
from . import views

urlpatterns = [
    path("album/<int:album_id>/rate/", views.rate_album, name="rate_album"),
    path("track/<int:track_id>/rate/", views.rate_track, name="rate_track"),
]
