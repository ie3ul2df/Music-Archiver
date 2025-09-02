from django.db import models
from django.conf import settings


class Album(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="albums"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"



class AlbumTrack(models.Model):
    """
    Explicit through model to preserve per-album track order.
    """
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="items",
    )
    track = models.ForeignKey(
        "tracks.Track",
        on_delete=models.CASCADE,
        related_name="album_items",
    )
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("album", "track"),)
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.album.name} → {self.track.name} (#{self.position})"
