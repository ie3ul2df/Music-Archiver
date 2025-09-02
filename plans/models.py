from django.db import models
from django.contrib.auth.models import User

class Plan(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    period = models.CharField(max_length=50, default="Life-Time")
    # existing toggles
    is_unlimited_tracks = models.BooleanField(default=False)
    is_unlimited_playlists = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    # NEW: how much storage this plan grants (can be summed if multiple)
    storage_gb = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    """Which plan a user has subscribed to"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'No Plan'}"
