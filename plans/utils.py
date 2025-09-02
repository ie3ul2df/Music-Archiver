from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Sum
from .models import Plan
from checkout.models import OrderItem
from tracks.models import Track

@dataclass
class Entitlements:
    unlimited_tracks: bool = False
    unlimited_playlists: bool = False
    premium: bool = False
    storage_gb: int = 0

DEFAULT_MAX_TRACKS = 10
DEFAULT_MAX_PLAYLISTS = 1

def get_entitlements(user) -> Entitlements:
    ent = Entitlements()
    if not user.is_authenticated:
        return ent

    items = (OrderItem.objects
             .filter(order__user=user)
             .select_related("plan"))

    for it in items:
        p = it.plan
        if getattr(p, "is_unlimited_tracks", False):
            ent.unlimited_tracks = True
        if getattr(p, "is_unlimited_playlists", False):
            ent.unlimited_playlists = True
        if getattr(p, "is_premium", False):
            ent.premium = True
        if getattr(p, "storage_gb", 0):
            ent.storage_gb += int(p.storage_gb)

    return ent

def can_add_track(user):
    ent = get_entitlements(user)
    if ent.unlimited_tracks or ent.premium:
        return True, None
    count = Track.objects.filter(user=user).count()
    return (count < DEFAULT_MAX_TRACKS,
            "Free tier limit reached (10 tracks). Upgrade a plan to add more.")

def can_add_playlist(user):
    ent = get_entitlements(user)
    if ent.unlimited_playlists or ent.premium:
        return True, None
    from playlist.models import Playlist
    count = Playlist.objects.filter(user=user).count()
    return (count < DEFAULT_MAX_PLAYLISTS,
            "Free tier limit reached (1 playlist). Upgrade a plan to add more.")

def can_upload_file(user, file_size_bytes: int):
    ent = get_entitlements(user)
    if ent.storage_gb <= 0:
        return False, "No storage plan. Buy storage to upload audio files."

    # Sum current usage
    from django.db.models.functions import Coalesce
    qs = Track.objects.filter(user=user).exclude(audio_file="")
    # file size retrieval is filesystem-level; keep a light estimate:
    used = 0
    for t in qs:
        try:
            if t.audio_file and hasattr(t.audio_file, "size"):
                used += t.audio_file.size
        except Exception:
            pass

    quota = ent.storage_gb * (1024**3)
    return (used + file_size_bytes <= quota,
            f"Storage quota exceeded. You have {ent.storage_gb}GB total.")
