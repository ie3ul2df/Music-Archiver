# playlist/context_processors.py
from playlist.models import Playlist, PlaylistItem

def playlist_membership(request):
    """
    Make the current user's playlist membership available on every page.
    Returns {'in_playlist_ids': [<track_id>, ...]} or an empty list.
    """
    ids = []
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"in_playlist_ids": ids}

    pl = Playlist.objects.filter(owner=user, name="My Playlist").first()
    if not pl:
        return {"in_playlist_ids": ids}

    ids = list(
        PlaylistItem.objects.filter(playlist=pl).values_list("track_id", flat=True)
    )
    return {"in_playlist_ids": ids}
