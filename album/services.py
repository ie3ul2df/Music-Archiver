# album/services.py
from django.db.models import Avg, Count, Exists, OuterRef, Prefetch

from album.models import AlbumTrack
from playlist.models import Playlist, PlaylistItem
from ratings.utils import annotate_albums
from tracks.models import Favorite
from tracks.utils import annotate_is_in_my_albums


def hydrate_albums_for_cards(qs, user):
    """
    Prefetch album_tracks with per-track flags so that templates using
    _album_card.html + _track_card.html render correctly everywhere.
    Returns a list(albums) with:
      - at.is_favorited
      - at.track_avg, at.track_count
      - at.track.is_in_my_albums
      - at.track.in_playlist
      - album.rating_avg, album.rating_count (via annotate_albums)
    """

    # Per-track favourites + rating aggregates (on the through row)
    fav_subq = Favorite.objects.filter(owner=user, track=OuterRef("track_id"))
    at_qs = (
        AlbumTrack.objects.select_related("track", "track__owner")
        .annotate(
            is_favorited=Exists(fav_subq),
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("position", "id")
    )

    # Put the annotations onto the default relation name "album_tracks"
    qs = annotate_albums(qs).prefetch_related(Prefetch("album_tracks", queryset=at_qs))

    albums = list(qs)

    # Build the user's playlist membership set once
    in_playlist_ids = set()
    if getattr(user, "is_authenticated", False):
        pl = Playlist.objects.filter(owner=user, name="My Playlist").first()
        if pl:
            in_playlist_ids = set(
                PlaylistItem.objects.filter(playlist=pl).values_list(
                    "track_id", flat=True
                )
            )

    # Attach per-track flags used by _track_card.html
    for album in albums:
        ats = list(getattr(album, "album_tracks").all())

        # Saved/ownership union flag on each track (🗃 vs 💾)
        annotate_is_in_my_albums(ats, user, attr="track")

        # Playlist membership ✓/➕
        for at in ats:
            at.track.in_playlist = at.track.id in in_playlist_ids

    return albums
