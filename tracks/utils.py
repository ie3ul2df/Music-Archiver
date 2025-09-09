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
