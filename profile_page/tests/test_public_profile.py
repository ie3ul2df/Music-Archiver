from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from album.models import Album, AlbumTrack
from ratings.models import TrackRating
from tracks.models import Track


class PublicProfileRatingsTests(TestCase):
    def test_track_ratings_are_highlighted_using_average(self):
        owner = User.objects.create_user(username="owner", password="pw")
        rater = User.objects.create_user(username="rater", password="pw")
        track = Track.objects.create(owner=owner, name="Song")
        album = Album.objects.create(owner=owner, name="Public", is_public=True)
        AlbumTrack.objects.create(album=album, track=track)
        TrackRating.objects.create(user=rater, track=track, stars=4)

        response = self.client.get(
            reverse("profile:public_profile", args=[owner.username]), follow=True
        )

        self.assertContains(response, 'class="star-btn is-selected"')
        self.assertContains(response, '<span class="avg text-warning">4.0</span>')