# tracks/context_processors.py
from album.models import AlbumTrack
from save_system.models import SavedTrack
from tracks.models import Favorite, Track


def ui_track_state(request):
    """
    Globally expose:
      - favorite_ids: track IDs user has favourited
      - my_collection_ids: union of (own tracks)
      ∪ (in any of my albums) ∪ (explicitly saved)
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"favorite_ids": [], "my_collection_ids": []}

    favorite_ids = list(
        Favorite.objects.filter(owner=user).values_list("track_id", flat=True)
    )

    own_ids = list(Track.objects.filter(owner=user).values_list("id", flat=True))
    attached_ids = list(
        AlbumTrack.objects.filter(album__owner=user).values_list("track_id", flat=True)
    )
    saved_ids = list(
        SavedTrack.objects.filter(owner=user).values_list(
            "original_track_id", flat=True
        )
    )
    my_collection_ids = sorted(set(own_ids) | set(attached_ids) | set(saved_ids))

    return {
        "favorite_ids": favorite_ids,
        "my_collection_ids": my_collection_ids,
    }
