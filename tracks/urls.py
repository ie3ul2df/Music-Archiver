# ----------------------- tracks/urls.py ----------------------- #
from django.urls import path
from . import views

urlpatterns = [
    # Track list / main player
    path("", views.track_list, name="track_list"),

    # Favourites & Recently Played
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("recent/", views.recently_played, name="recently_played"),
    path("<int:track_id>/play/", views.play_track, name="play_track"),

    # API / AJAX for tracks
    path("api/tracks.json", views.tracks_json, name="tracks_json"),
    path("api/favorites/toggle/<int:track_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("api/plays/<int:track_id>/", views.log_play, name="log_play"),

    # Clear recent list
    path("tracks/api/recent/clear/", views.clear_recent, name="clear_recent"),

    # Legacy aliases (keep if you want backwards compatibility)
    path("json/", views.tracks_json, name="tracks_json_legacy"),
    path("<int:track_id>/fav/", views.toggle_favorite, name="toggle_favorite_legacy"),
    
    # Download track
    path("<int:pk>/download/", views.download_track, name="download_track"),
    
    # User tracks
    path("by/<str:username>/", views.user_tracks, name="user_tracks"),
    
    # Delete track
    path("<int:pk>/delete/", views.delete_track, name="delete_track"),
]
