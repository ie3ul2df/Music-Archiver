# tracks/utils.py
from typing import Iterable, Optional
from album.models import AlbumTrack
from save_system.models import SavedTrack
from playlist.models import Playlist, PlaylistItem

def annotate_is_in_my_albums(objs: Iterable, user, *, attr: Optional[str] = None):
    # --- your existing implementation unchanged ---
    # (keep exactly what you already have)
    items = list(objs)
    if not items:
        return objs
    if attr:
        tracks = [getattr(o, attr, None) for o in items]
        tracks = [t for t in tracks if t is not None]
    else:
        tracks = items
    if not user.is_authenticated:
        for t in tracks:
            setattr(t, "is_in_my_albums", False)
        return objs
    ids = {getattr(t, "id", None) for t in tracks}
    ids.discard(None)
    if not ids:
        for t in tracks:
            setattr(t, "is_in_my_albums", False)
        return objs
    own_ids = {t.id for t in tracks if getattr(t, "owner_id", None) == user.id}
    attached_ids = set(
        AlbumTrack.objects.filter(album__owner=user, track_id__in=ids)
        .values_list("track_id", flat=True)
    )
    saved_ids = set(
        SavedTrack.objects.filter(owner=user, original_track_id__in=ids)
        .values_list("original_track_id", flat=True)
    )
    in_ids = own_ids | attached_ids | saved_ids
    for t in tracks:
        setattr(t, "is_in_my_albums", getattr(t, "id", None) in in_ids)
    return objs

def mark_track_ownership(tracks, user):
    # --- your existing implementation unchanged ---
    uid = getattr(user, "id", None)
    if not uid:
        for t in tracks:
            obj = getattr(t, "track", t)
            obj.is_my_track = False
        return tracks
    for t in tracks:
        obj = getattr(t, "track", t)
        obj.is_my_track = (obj.owner_id == uid)
    return tracks

# NEW: annotate playlist membership on Track objects (works for Track or AlbumTrack lists)
def annotate_in_playlist(objs: Iterable, user, *, attr: Optional[str] = None):
    """
    Set .in_playlist on Track objects for the user's 'My Playlist'.
    objs:
      - Iterable[Track]           -> attr=None
      - Iterable[... with .track] -> attr='track'
    """
    items = list(objs)
    if not items:
        return objs

    tracks = [getattr(o, attr) if attr else o for o in items]
    tracks = [t for t in tracks if t is not None]

    if not getattr(user, "is_authenticated", False):
        for t in tracks:
            setattr(t, "in_playlist", False)
        return objs

    pl = Playlist.objects.filter(owner=user, name="My Playlist").first()
    in_ids = set()
    if pl:
        in_ids = set(PlaylistItem.objects.filter(playlist=pl).values_list("track_id", flat=True))

    for t in tracks:
        setattr(t, "in_playlist", getattr(t, "id", None) in in_ids)

    return objs
