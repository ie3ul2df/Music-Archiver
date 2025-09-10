from django.db import models
from django.conf import settings
from tracks.models import Track

class Playlist(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists"
    )
    name = models.CharField(max_length=120, default="My Playlist")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "name")

    def __str__(self):
        return f"{self.name} ({self.owner})"


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="items"
    )
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0, db_index=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("playlist", "track")
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.playlist} → {self.track} @ {self.position}"
