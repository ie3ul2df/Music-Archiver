# tracks/utils.py
from typing import Iterable, Optional
from album.models import AlbumTrack
from save_system.models import SavedTrack

def annotate_is_in_my_albums(objs: Iterable, user, *, attr: Optional[str] = None):
    """
    Set .is_in_my_albums on Track objects.

    objs:
      - Iterable of Track                -> attr=None (default)
      - Iterable of objects with .track -> attr="track"

    Rule:
      is_in_my_albums = (I own the track) OR (track is in any of my albums) OR (I explicitly saved it)
    """
    items = list(objs)
    if not items:
        return objs

    # Extract Track instances (either objs are Track, or have .track)
    if attr:
        tracks = [getattr(o, attr, None) for o in items]
        tracks = [t for t in tracks if t is not None]
    else:
        tracks = items  # assume these ARE Track instances

    if not user.is_authenticated:
        for t in tracks:
            setattr(t, "is_in_my_albums", False)
        return objs

    # Collect IDs
    ids = {getattr(t, "id", None) for t in tracks}
    ids.discard(None)
    if not ids:
        for t in tracks:
            setattr(t, "is_in_my_albums", False)
        return objs

    # Own tracks
    own_ids = {t.id for t in tracks if getattr(t, "owner_id", None) == user.id}

    # Tracks attached to any of MY albums
    attached_ids = set(
        AlbumTrack.objects.filter(album__owner=user, track_id__in=ids)
        .values_list("track_id", flat=True)
    )

    # Tracks I explicitly saved (SavedTrack)
    saved_ids = set(
        SavedTrack.objects.filter(owner=user, original_track_id__in=ids)
        .values_list("original_track_id", flat=True)
    )

    in_ids = own_ids | attached_ids | saved_ids

    for t in tracks:
        setattr(t, "is_in_my_albums", getattr(t, "id", None) in in_ids)

    return objs



def mark_track_ownership(tracks, user):
    """
    Given a queryset or list of Track objects (or AlbumTrack with .track),
    attach a boolean flag .is_my_track on each track.
    """
    if not user.is_authenticated:
        for t in tracks:
            obj = getattr(t, "track", t)  # AlbumTrack vs Track
            obj.is_my_track = False
        return tracks

    uid = user.id
    for t in tracks:
        obj = getattr(t, "track", t)
        obj.is_my_track = (obj.owner_id == uid)
    return tracks
