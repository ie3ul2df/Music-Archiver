from django.db import models
from django.conf import settings
from album.models import Album 

def track_upload_to(instance, filename):
    """Uploads go into user-specific folders."""
    return f"user_{instance.user.id}/tracks/{filename}"


class Track(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tracks"
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="tracks",   # <-- this must exist
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    source_url = models.URLField(blank=True, null=True)
    audio_file = models.FileField(upload_to=track_upload_to, blank=True, null=True)
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)