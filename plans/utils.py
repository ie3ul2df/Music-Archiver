# plans/utils.py
from dataclasses import dataclass
from django.db.models import Sum
from tracks.models import Track
from checkout.models import OrderItem

@dataclass
class Entitlements:
    unlimited_tracks: bool = False
    unlimited_albums: bool = False  # we treat this as "unlimited albums"
    premium: bool = False
    storage_gb: int = 0

FREE_MAX_TRACKS_PER_ALBUM = 10
FREE_MAX_ALBUMS = 3  # Default Album only

def get_entitlements(user) -> Entitlements:
    ent = Entitlements()
    if not user.is_authenticated:
        return ent

    # Read from purchased OrderItems
    items = (OrderItem.objects
             .filter(order__user=user)
             .select_related("plan"))
    for it in items:
        p = it.plan
        if getattr(p, "is_unlimited_tracks", False):
            ent.unlimited_tracks = True
        if getattr(p, "is_unlimited_albums", False):
            ent.unlimited_albums = True
        if getattr(p, "is_premium", False):
            ent.premium = True
        if getattr(p, "storage_gb", 0):
            ent.storage_gb += int(p.storage_gb or 0)

    return ent


def can_add_album(user):
    """Free: 3 album max; Unlimited Albums or Premium: unlimited."""
    ent = get_entitlements(user)
    if ent.premium or ent.unlimited_albums:
        return True, None
    from album.models import Album
    count = Album.objects.filter(owner=user).count()
    if count >= FREE_MAX_ALBUMS:
        return False, "Free tier allows only 3 albums. Upgrade to add more."
    return True, None


def can_add_track(user, album):
    """
    Free & Unlimited Albums only: 10 per album (links).
    Unlimited Tracks or Premium: unlimited tracks.
    """
    ent = get_entitlements(user)
    if ent.premium or ent.unlimited_tracks:
        return True, None
    # cap per album
    count = Track.objects.filter(owner=user, album=album).count()
    if count >= FREE_MAX_TRACKS_PER_ALBUM:
        return False, "Album limit reached (10 tracks). Upgrade Unlimited Tracks or Premium."
    return True, None


def user_has_storage_plan(user) -> bool:
    return get_entitlements(user).storage_gb > 0


def can_upload_file(user, file_size_bytes: int):
    """
    Allow uploads only if storage_gb > 0 and within quota (sum of audio_file sizes).
    """
    ent = get_entitlements(user)
    if ent.storage_gb <= 0:
        return False, "No storage plan. Buy storage to upload audio files."

    # Compute used bytes across uploaded files
    used = 0
    for t in Track.objects.filter(owner=user).exclude(audio_file=""):
        try:
            if t.audio_file and hasattr(t.audio_file, "size"):
                used += t.audio_file.size
        except Exception:
            pass
    quota = ent.storage_gb * (1024 ** 3)
    if used + int(file_size_bytes or 0) > quota:
        gb_used = used / (1024 ** 3)
        return False, f"Storage quota exceeded ({gb_used:.2f}GB used of {ent.storage_gb}GB)."
    return True, None
