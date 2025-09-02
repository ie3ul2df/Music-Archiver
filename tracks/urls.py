from django.urls import path
from . import views

urlpatterns = [
    path("", views.track_list, name="track_list"),
    path("add/", views.track_create, name="track_create"),          # keep existing route
    path("<int:pk>/edit/", views.track_update, name="track_update"),
    path("<int:pk>/delete/", views.track_delete, name="track_delete"),
    # New endpoints for player feed and drag-and-drop ordering:
    path("json/", views.tracks_json, name="tracks_json"),
    path("reorder/", views.reorder_tracks, name="reorder_tracks"),
]
