# ----------------------- album/urls.py ----------------------- #
# album/urls.py
from django.urls import path
from . import views

app_name = "album"

urlpatterns = [
    # List & detail
    path("", views.album_list, name="album_list"),
    path("<int:pk>/", views.album_detail, name="album_detail"),

    # Drag & drop / search
    path("reorder/", views.albums_reorder, name="albums_reorder"),
    path("search/", views.unified_search, name="unified_search"),

    # Public view
    path("p/<slug:slug>/", views.public_album_detail, name="public_album_detail"),

    # AJAX CRUD
    path("api/add/", views.ajax_add_album, name="ajax_add_album"),
    path("<int:pk>/rename/", views.ajax_rename_album, name="ajax_rename_album"),
    path("<int:pk>/delete/", views.ajax_delete_album, name="ajax_delete_album"),

    # Tracks inside an album
    path("<int:pk>/tracks/add/", views.album_add_track, name="album_add_track"),
    path("<int:pk>/tracks/reorder/", views.album_reorder_tracks, name="album_reorder_tracks"),
    path("<int:pk>/tracks/<int:item_id>/rename/", views.album_rename_track, name="album_rename_track"),

    # ⛔ Detach (new canonical name)
    path("<int:pk>/tracks/<int:item_id>/detach/", views.album_detach_track, name="album_detach_track"),
    path("<int:pk>/tracks/bulk-detach/", views.album_bulk_detach, name="album_bulk_detach"),

    # (Optional alias for any old code still calling “remove”)
    path("<int:pk>/tracks/<int:item_id>/remove/", views.album_detach_track, name="album_remove_track"),

    # Visibility
    path("<int:pk>/toggle-visibility/", views.toggle_album_visibility, name="toggle_album_visibility"),
    
    path("fragment/<int:pk>/tracks/", views.album_tracks_fragment, name="album_tracks_fragment"),
]
