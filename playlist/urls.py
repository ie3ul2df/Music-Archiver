from django.urls import path
from . import views

urlpatterns = [
    # Lists & CRUD
    path("", views.playlist_list, name="playlist_list"),
    path("add/", views.playlist_create, name="playlist_create"),
    path("<int:pk>/", views.playlist_detail, name="playlist_detail"),
    path("<int:pk>/edit/", views.playlist_update, name="playlist_update"),
    path("<int:pk>/delete/", views.playlist_delete, name="playlist_delete"),

    # Track management inside a playlist
    path("<int:pk>/tracks/add/", views.playlist_add_track, name="playlist_add_track"),
    path("<int:pk>/tracks/<int:item_id>/remove/", views.playlist_remove_track, name="playlist_remove_track"),
    path("<int:pk>/tracks/reorder/", views.playlist_reorder, name="playlist_reorder"),

    # Reorder playlists (top-level list)
    path("reorder/", views.playlists_reorder, name="playlists_reorder"),
]
