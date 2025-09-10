from django.contrib import admin
from .models import Playlist, PlaylistItem

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "name", "created_at")
    list_filter = ("owner",)
    search_fields = ("name", "owner__username")

@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "playlist", "track", "position", "added_at")
    list_filter = ("playlist",)
    search_fields = ("track__name",)
