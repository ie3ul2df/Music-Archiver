from django.conf import settings
from django.db import models

from album.models import Album
from tracks.models import Track


class CloudAccount(models.Model):
    PROVIDERS = [("gdrive", "Google Drive")]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cloud_accounts",
    )
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    label = models.CharField(max_length=120, default="Google Drive")
    token_json = models.TextField()  # stores OAuth creds JSON (access + refresh)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} · {self.get_provider_display()}"


class CloudFolderLink(models.Model):
    album = models.OneToOneField(
        Album, on_delete=models.CASCADE, related_name="cloud_link"
    )
    account = models.ForeignKey(
        CloudAccount, on_delete=models.CASCADE, related_name="folder_links"
    )
    folder_id = models.CharField(max_length=200)  # provider folder ID
    display_path = models.CharField(max_length=500, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.album} ← {self.account.label}:{self.folder_id}"


class CloudFileMap(models.Model):
    """Map a provider file to a Track so sync updates (no dupes)."""

    link = models.ForeignKey(
        CloudFolderLink, on_delete=models.CASCADE, related_name="files"
    )
    file_id = models.CharField(max_length=200, db_index=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    name = models.CharField(max_length=300)
    mime = models.CharField(max_length=100, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    etag = models.CharField(max_length=200, blank=True)  # md5/etag-ish

    class Meta:
        unique_together = (("link", "file_id"),)

    def __str__(self):
        return f"{self.link.album} · {self.name}"
