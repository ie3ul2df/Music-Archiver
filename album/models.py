# ----------------------- album/models.py ----------------------- #
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Q
from django.db.models.deletion import ProtectedError
import uuid


class Album(models.Model):
    """Music album belonging to a user, grouping tracks in order."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="albums",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    slug = models.SlugField(max_length=180, unique=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["owner", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(is_default=True),
                name="uniq_default_album_per_owner",
            )
        ]

    def _make_unique_slug(self) -> str:
        """
        Generate a unique slug for the album based on its name.
        Falls back to a UUID snippet if too many conflicts.
        """
        base = slugify(self.name) or "album"
        slug = base
        i = 1
        Model = self.__class__

        while Model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            i += 1
            slug = f"{base}-{i}"
            if i > 30:  # safety fallback
                slug = f"{base}-{uuid.uuid4().hex[:8]}"
                break
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._make_unique_slug()
        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        if self.is_default:
            raise ProtectedError("Default albums cannot be deleted.", [self])
        return super().delete(*args, **kwargs)


    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class AlbumTrack(models.Model):
    """Through model linking albums and tracks, with explicit ordering."""

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="album_tracks",
    )
    track = models.ForeignKey(
        "tracks.Track",
        on_delete=models.CASCADE,
        related_name="track_albums",
    )
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Users can rename other users track on their own album only without changing the original track name
    custom_name = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        unique_together = (("album", "track"),)
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["album", "position"],
                name="uniq_album_position",
            )
        ]
        indexes = [models.Index(fields=["album", "position"])]

    def save(self, *args, **kwargs):
        """
        Ensure newly created items get a position at the end of the album
        if the caller doesn't provide one, but avoid interfering when
        updating an existing object's position (e.g. via drag-and-drop
        reordering).
        """
        if self._state.adding and self.position == 0:
            last = (
                AlbumTrack.objects.filter(album=self.album)
                .order_by("-position")
                .first()
            )
            self.position = (last.position + 1) if last else 0
        super().save(*args, **kwargs)

    def __str__(self):
        track_label = getattr(self.track, "title", None) or getattr(self.track, "name", None) or str(self.track)
        return f"{self.album.name} → {track_label} (#{self.position})"
