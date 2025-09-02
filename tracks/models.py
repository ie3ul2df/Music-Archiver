from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

class Track(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tracks")
    name = models.CharField(max_length=255)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    source_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return self.name


User = get_user_model()

def track_upload_to(instance, filename):
    return f"tracks/{instance.user_id}/{filename}"

class Track(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tracks")
    name = models.CharField(max_length=200)
    source_url = models.URLField(blank=True, null=True)           # external link
    audio_file = models.FileField(upload_to=track_upload_to, blank=True, null=True)  # uploaded file
    position = models.PositiveIntegerField(default=0, db_index=True)  # global order per user
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name