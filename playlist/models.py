from django.db import models
from django.conf import settings


class Playlist(models.Model):
    """A playlist created by a user containing multiple tracks (ordered)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Use a through model so we can store per-playlist track order.
    tracks = models.ManyToManyField(
        'tracks.Track',
        related_name='playlists',
        blank=True,
        through='PlaylistTrack',
        through_fields=('playlist', 'track'),
    )

    # Optional: order playlists for a user
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PlaylistTrack(models.Model):
    """
    Explicit through model to preserve per-playlist track order.
    """
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    track = models.ForeignKey(
        'tracks.Track',
        on_delete=models.CASCADE,
        related_name="playlist_items",
    )
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("playlist", "track"),)
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.playlist.name} → {self.track.name} (#{self.position})"
