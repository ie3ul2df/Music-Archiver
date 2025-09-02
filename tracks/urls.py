# ----------------------- tracks/urls.py ----------------------- #

from django.urls import path
from . import views

urlpatterns = [
    # Music Player page (tracks + albums)
    path("", views.track_list, name="track_list"),
    # Albums
    path("albums/", views.album_list, name="album_list"),
    path("albums/<int:pk>/", views.album_detail, name="album_detail"),
    # Player feed + ordering
    path("json/", views.tracks_json, name="tracks_json"),
    path("reorder/", views.reorder_tracks, name="reorder_tracks"),
    # AJAX endpoints
    path("albums/add/", views.ajax_add_album, name="ajax_add_album"),
    path("albums/<int:pk>/rename/", views.ajax_rename_album, name="ajax_rename_album"),
    path("albums/<int:pk>/delete/", views.ajax_delete_album, name="ajax_delete_album"),
    # RecentTracks (and play)
    path("<int:pk>/play/", views.play_track, name="play_track"),
    path("recent/", views.recently_played, name="recently_played"),
    #Favorites
    path("<int:pk>/fav/", views.toggle_favorite, name="toggle_favorite"),
    path("favorites/", views.favorites_list, name="favorites_list"),
]
