from django.urls import path
from . import views

app_name = "playlist"

urlpatterns = [
    path("json/", views.playlist_json, name="json"),
    path("toggle/<int:track_id>/", views.playlist_toggle, name="toggle"),
    path("reorder/", views.playlist_reorder, name="reorder"),
    path("clear/", views.playlist_clear, name="clear"),
]
