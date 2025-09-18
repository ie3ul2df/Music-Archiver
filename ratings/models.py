from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AlbumRating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="album_ratings",
    )
    album = models.ForeignKey(
        "album.Album",
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "album"),)
        indexes = [models.Index(fields=["album", "user"])]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} ★{self.stars} {self.album}"


class TrackRating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="track_ratings",
    )
    track = models.ForeignKey(
        "tracks.Track",
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "track"),)
        indexes = [models.Index(fields=["track", "user"])]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} ★{self.stars} {self.track}"
