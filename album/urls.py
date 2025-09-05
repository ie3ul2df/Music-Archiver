# ----------------------- album/urls.py ----------------------- #

from django.urls import path
from . import views

app_name = "album"  # ✅ allows {% url 'album:album_detail' pk %} safely

urlpatterns = [
    # Album list & CRUD
    path("", views.album_list, name="album_list"),                     # list all albums
    path("add/", views.album_create, name="album_create"),             # create album
    path("<int:pk>/", views.album_detail, name="album_detail"),        # single album detail
    path("<int:pk>/edit/", views.album_update, name="album_update"),   # rename/update album
    path("<int:pk>/delete/", views.album_delete, name="album_delete"), # delete album
    path("search/", views.album_search, name="album_search"),          # search albums

    # Track management inside an album
    path("<int:pk>/tracks/add/", views.album_add_track, name="album_add_track"),
    path("<int:pk>/tracks/<int:item_id>/remove/", views.album_remove_track, name="album_remove_track"),
    path("<int:pk>/tracks/reorder/", views.album_reorder_tracks, name="album_reorder_tracks"),

    # Reorder albums (top-level list)
    path("reorder/", views.albums_reorder, name="albums_reorder"),

    # Sharing & visibility
    path("p/<slug:slug>/", views.public_album_detail, name="public_album_detail"),
    path("<int:pk>/toggle-visibility/", views.toggle_album_visibility, name="toggle_album_visibility"),
]
