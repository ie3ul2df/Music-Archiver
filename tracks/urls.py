# ----------------------- tracks/urls.py ----------------------- #
from django.urls import path
from . import views

urlpatterns = [
    # ===== Pages (HTML) =====
    path("", views.track_list, name="track_list"),
    path("albums/", views.album_list, name="album_list"),
    path("albums/<int:album_id>/", views.album_detail, name="album_detail"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("recent/", views.recently_played, name="recently_played"),
    path("<int:track_id>/play/", views.play_track, name="play_track"),

    # ===== API / AJAX =====
    path("api/tracks.json", views.tracks_json, name="tracks_json"),
    path("api/tracks/reorder/", views.reorder_tracks, name="reorder_tracks"),
    path("api/favorites/toggle/<int:track_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("api/plays/<int:track_id>/", views.log_play, name="log_play"),

    # Album AJAX
    path("api/albums/add/", views.ajax_add_album, name="ajax_add_album"),
    path("api/albums/<int:album_id>/rename/", views.ajax_rename_album, name="ajax_rename_album"),
    path("api/albums/<int:album_id>/delete/", views.ajax_delete_album, name="ajax_delete_album"),

    # ===== Legacy aliases (optional) =====
    path("json/", views.tracks_json, name="tracks_json_legacy"),
    path("reorder/", views.reorder_tracks, name="reorder_tracks_legacy"),
    path("<int:track_id>/fav/", views.toggle_favorite, name="toggle_favorite_legacy"),
]
