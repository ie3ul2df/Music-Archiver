# ----------------------- tracks/models.py ----------------------- #

from django.db import models
from django.conf import settings

def track_upload_to(instance, filename):
    """Uploads go into owner-specific folders."""
    uid = getattr(instance, "owner_id", None) or "anon"
    return f"user_{uid}/tracks/{filename}"


class Track(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracks"
    )

    name = models.CharField(max_length=200, default="(untitled)")
    audio_file = models.FileField(upload_to="tracks/", blank=True, null=True)
    source_url = models.URLField(blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    play_count = models.PositiveIntegerField(default=0)
    last_played_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class Favorite(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_tracks",
        related_query_name="favorite_track",
    )
    track = models.ForeignKey(
        "Track",
        on_delete=models.CASCADE,
        related_name="favorited_by",
        related_query_name="favorite_user",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW: persisted sort order
    position = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("owner", "track"),)
        ordering = ["position", "-created_at"]  # <- use saved order first
        indexes = [
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["owner", "position"]),
        ]



class Listen(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listens")
    track = models.ForeignKey("Track", on_delete=models.CASCADE, related_name="listens")
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-played_at"])]
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.user} ▶ {self.track} @ {self.played_at:%Y-%m-%d %H:%M}"