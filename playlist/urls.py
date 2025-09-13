from django.urls import path
from . import views

app_name = "playlist"

urlpatterns = [
    path("json/", views.playlist_json, name="json"),
    path("toggle/<int:track_id>/", views.playlist_toggle, name="toggle"),
    path("clear/", views.playlist_clear, name="clear"),
    path("bulk-add/", views.bulk_add_to_playlist, name="bulk_add"),
    path("reorder/", views.reorder, name="reorder"),
]
