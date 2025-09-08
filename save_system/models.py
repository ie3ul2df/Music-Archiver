from django.db import models
from django.conf import settings
from django.utils import timezone

# Import your existing models
from album.models import Album
from tracks.models import Track

def _safe_str(x):
    try:
        return str(x)
    except Exception:
        return ""

def _get_name(obj):
    # tolerate title/name differences
    for attr in ("name", "title"):
        if hasattr(obj, attr) and getattr(obj, attr):
            return getattr(obj, attr)
    return _safe_str(obj)

def _get_description(obj):
    for attr in ("description", "desc", "summary"):
        if hasattr(obj, attr) and getattr(obj, attr):
            return getattr(obj, attr) or ""
    return ""

class SavedAlbum(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_albums",
    )
    # Keep the record even if original is deleted (snapshot still useful)
    original_album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saves",
    )
    name_snapshot = models.CharField(max_length=200)
    description_snapshot = models.TextField(blank=True)
    saved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("owner", "original_album"),)
        indexes = [
            models.Index(fields=["owner", "saved_at"]),
        ]
        ordering = ["-saved_at"]

    def __str__(self):
        base = self.name_snapshot or "(unnamed album)"
        return f"{self.owner} saved “{base}”"

    @property
    def has_updates(self):
        """True if current album metadata differs from the snapshot."""
        if not self.original_album:
            # original deleted -> definitely 'changed'
            return True
        current_name = _get_name(self.original_album)
        current_desc = _get_description(self.original_album)
        return (
            (current_name or "") != (self.name_snapshot or "") or
            (current_desc or "") != (self.description_snapshot or "")
        )

class SavedTrack(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_tracks",
    )
    original_track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="saves",
    )
    # The user's own album to file it into
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="saved_tracks",
    )
    name_snapshot = models.CharField(max_length=200)
    saved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("owner", "original_track", "album"),)
        indexes = [
            models.Index(fields=["owner", "saved_at"]),
            models.Index(fields=["album", "saved_at"]),
        ]
        ordering = ["-saved_at"]

    def __str__(self):
        base = self.name_snapshot or "(unnamed track)"
        return f"{self.owner} saved track “{base}” → {self.album}"

    @property
    def has_updates(self):
        if not self.original_track:
            return True
        current_name = _get_name(self.original_track)
        return (current_name or "") != (self.name_snapshot or "")
