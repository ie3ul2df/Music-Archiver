from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Plan

@receiver(post_migrate)
def create_default_plans(sender, **kwargs):
    if sender.name == "plans" and Plan.objects.count() == 0:
        Plan.objects.create(
            name="Unlimited Tracks",
            price=10.00,
            description="Unlimited tracks per playlist.",
            is_unlimited_tracks=True
        )
        Plan.objects.create(
            name="Unlimited Playlists",
            price=10.00,
            description="Unlimited playlists, but track limit applies.",
            is_unlimited_playlists=True
        )
        Plan.objects.create(
            name="Premium",
            price=15.00,
            description="Unlimited tracks and playlists.",
            is_unlimited_tracks=True,
            is_unlimited_playlists=True
        )
