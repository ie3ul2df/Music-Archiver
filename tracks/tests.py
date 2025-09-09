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
        ids = [fav.id for fav in favorites]
        # Favorites should be returned in reverse creation order by default
        self.assertEqual(ids, [t3.id, t2.id, t1.id])

    def test_recent_follow_track_position(self):
        now = timezone.now()
        t1 = Track.objects.create(owner=self.user, name="t1", position=2)
        t2 = Track.objects.create(owner=self.user, name="t2", position=1)
        t3 = Track.objects.create(owner=self.user, name="t3", position=3)
        l1 = Listen.objects.create(user=self.user, track=t1)
        l2 = Listen.objects.create(user=self.user, track=t2)
        l3 = Listen.objects.create(user=self.user, track=t3)
        Listen.objects.filter(pk=l1.pk).update(played_at=now)
        Listen.objects.filter(pk=l2.pk).update(played_at=now - timedelta(minutes=1))
        Listen.objects.filter(pk=l3.pk).update(played_at=now - timedelta(minutes=2))

        response = self.client.get(reverse("track_list"))
        recent = response.context["recent"]
        ids = [trk.id for trk in recent]
        self.assertEqual(ids, [t1.id, t2.id, t3.id])