from django.contrib import admin

from .models import SavedAlbum, SavedTrack


@admin.register(SavedAlbum)
class SavedAlbumAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "name_snapshot",
        "original_album",
        "saved_at",
        "has_updates",
    )
    list_filter = ("owner",)
    search_fields = ("name_snapshot",)


@admin.register(SavedTrack)
class SavedTrackAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "name_snapshot",
        "album",
        "original_track",
        "saved_at",
        "has_updates",
    )
    list_filter = ("owner", "album")
    search_fields = ("name_snapshot",)
