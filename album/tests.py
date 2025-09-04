import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from album.models import Album, AlbumTrack
from tracks.models import Track

class AlbumReorderTracksTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u", password="pw")
        self.client.login(username="u", password="pw")
        self.album = Album.objects.create(owner=self.user, name="A")
        t1 = Track.objects.create(owner=self.user, name="T1")
        t2 = Track.objects.create(owner=self.user, name="T2")
        self.at1 = AlbumTrack.objects.create(album=self.album, track=t1, position=0)
        self.at2 = AlbumTrack.objects.create(album=self.album, track=t2, position=1)

    def test_reorder_swaps_positions(self):
        url = reverse("album:album_reorder_tracks", args=[self.album.pk])
        data = {"order": [self.at2.id, self.at1.id]}
        resp = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.at1.refresh_from_db()
        self.at2.refresh_from_db()
        self.assertEqual(self.at1.position, 1)
        self.assertEqual(self.at2.position, 0)