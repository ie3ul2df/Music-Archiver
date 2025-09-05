from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Track, Favorite, Listen


class TrackListOrderingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_login(self.user)

    def test_favorites_follow_track_position(self):
        t1 = Track.objects.create(owner=self.user, name="t1", position=2)
        t2 = Track.objects.create(owner=self.user, name="t2", position=1)
        t3 = Track.objects.create(owner=self.user, name="t3", position=3)
        Favorite.objects.create(owner=self.user, track=t1)
        Favorite.objects.create(owner=self.user, track=t2)
        Favorite.objects.create(owner=self.user, track=t3)

        response = self.client.get(reverse("track_list"))
        favorites = list(response.context["favorites"])
        ids = [fav.track.id for fav in favorites]
        self.assertEqual(ids, [t2.id, t1.id, t3.id])

    def test_recent_follow_track_position(self):
        now = timezone.now()
        t1 = Track.objects.create(owner=self.user, name="t1", position=2)
        t2 = Track.objects.create(owner=self.user, name="t2", position=1)
        t3 = Track.objects.create(owner=self.user, name="t3", position=3)
        Listen.objects.create(user=self.user, track=t1, played_at=now)
        Listen.objects.create(user=self.user, track=t2, played_at=now - timedelta(minutes=1))
        Listen.objects.create(user=self.user, track=t3, played_at=now - timedelta(minutes=2))

        response = self.client.get(reverse("track_list"))
        recent = response.context["recent"]
        ids = [row["track"].id for row in recent]
        self.assertEqual(ids, [t2.id, t1.id, t3.id])