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
            is_unlimited_tracks=True,
            period="Life-Time"
        )
        Plan.objects.create(
            name="Unlimited Playlists",
            price=10.00,
            description="Unlimited playlists, but track limit applies.",
            is_unlimited_playlists=True,
            period="Life-Time"
        )
        Plan.objects.create(
            name="Premium",
            price=15.00,
            description="Unlimited tracks and playlists.",
            is_unlimited_tracks=True,
            is_unlimited_playlists=True,
            period="Life-Time"
        )
        # storage plans
        Plan.objects.create(
            name="1GB Storage",
            price=7.00,
            description="Get 1GB cloud storage for your music data.",
            period="4-Years"
        )
        Plan.objects.create(
            name="5GB Storage",
            price=15.00,
            description="Get 5GB cloud storage for your music data.",
            period="4-Years"
        )
        Plan.objects.create(
            name="10GB Storage",
            price=20.00,
            description="Get 10GB cloud storage for your music data.",
            period="4-Years"
        )