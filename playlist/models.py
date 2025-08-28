from django.db import models
from django.contrib.auth.models import User
from tracks.models import Track


class Playlist(models.Model):
    """A playlist created by a user containing multiple tracks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    tracks = models.ManyToManyField(Track, related_name="playlists", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"
