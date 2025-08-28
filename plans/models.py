from django.db import models
from django.contrib.auth.models import User

class Plan(models.Model):
    """Subscription plans available to users"""
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    is_unlimited_tracks = models.BooleanField(default=False)
    is_unlimited_playlists = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (£{self.price})"


class UserSubscription(models.Model):
    """Which plan a user has subscribed to"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'No Plan'}"
