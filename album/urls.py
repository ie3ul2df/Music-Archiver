# ----------------------- album/urls.py ----------------------- #
from django.urls import path
from . import views

app_name = "album"  # allows {% url 'album:...' %}

urlpatterns = [
    # ---------- List & detail ----------
    path("", views.album_list, name="album_list"),                 # GET: list user's albums
    path("<int:pk>/", views.album_detail, name="album_detail"),    # GET: album detail page

    # ---------- Drag & drop / search ----------
    path("reorder/", views.albums_reorder, name="albums_reorder"),       # POST: reorder user's albums
    path("search/", views.album_search, name="album_search"),            # GET (AJAX): search user's albums

    # Public view (slug so it doesn’t clash with pk)
    path("p/<slug:slug>/", views.public_album_detail, name="public_album_detail"),

    # ---------- AJAX CRUD ----------
    path("api/add/", views.ajax_add_album, name="ajax_add_album"),                # POST (AJAX): create
    path("<int:pk>/rename/", views.ajax_rename_album, name="ajax_rename_album"),  # POST (AJAX): rename
    path("<int:pk>/delete/", views.ajax_delete_album, name="ajax_delete_album"),  # POST (AJAX): delete

    # ---------- Tracks inside an album (names MUST match your templates/JS) ----------
    path("<int:pk>/tracks/add/", views.album_add_track, name="album_add_track"),
    path("<int:pk>/tracks/reorder/", views.album_reorder_tracks, name="album_reorder_tracks"),
    path("<int:pk>/tracks/<int:item_id>/rename/", views.album_rename_track, name="album_rename_track"),
    path("<int:pk>/tracks/<int:item_id>/remove/", views.album_remove_track, name="album_remove_track"),

    # ---------- Visibility ----------
    path("<int:pk>/toggle-visibility/", views.toggle_album_visibility, name="toggle_album_visibility"),
]
