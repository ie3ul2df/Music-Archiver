from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count
from django.template.loader import render_to_string

from album.models import Album
from tracks.models import Track
from .models import AlbumRating, TrackRating

def _require_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "auth_required"}, status=401)
    return None

def _clamp_stars(value, default=0):
    try:
        n = int(value)
    except Exception:
        return default
    return max(1, min(5, n))

@require_POST
def rate_album(request, album_id):
    if (resp := _require_auth(request)) is not None:
        return resp
    stars = _clamp_stars(request.POST.get("stars"), default=5)
    album = Album.objects.filter(id=album_id, is_public=True).first() or Album.objects.filter(id=album_id).first()
    if not album:
        return JsonResponse({"ok": False, "error": "album_not_found"}, status=404)

    obj, _ = AlbumRating.objects.update_or_create(
        user=request.user, album=album, defaults={"stars": stars}
    )
    agg = album.ratings.aggregate(avg=Avg("stars"), count=Count("id"))
    html = render_to_string(
        "ratings/_stars.html",
        {
            "type": "album",
            "id": album.id,
            "avg": agg["avg"] or 0,
            "count": agg["count"] or 0,
            "user_rating": obj.stars,
        },
        request=request,
    )
    return JsonResponse({"ok": True, "html": html, "avg": agg["avg"] or 0, "count": agg["count"] or 0})

@require_POST
def rate_track(request, track_id):
    if (resp := _require_auth(request)) is not None:
        return resp
    stars = _clamp_stars(request.POST.get("stars"), default=5)
    track = Track.objects.filter(id=track_id).first()
    if not track:
        return JsonResponse({"ok": False, "error": "track_not_found"}, status=404)

    obj, _ = TrackRating.objects.update_or_create(
        user=request.user, track=track, defaults={"stars": stars}
    )
    agg = track.ratings.aggregate(avg=Avg("stars"), count=Count("id"))
    html = render_to_string(
        "ratings/_stars.html",
        {
            "type": "track",
            "id": track.id,
            "avg": agg["avg"] or 0,
            "count": agg["count"] or 0,
            "user_rating": obj.stars,
        },
        request=request,
    )
    return JsonResponse({"ok": True, "html": html, "avg": agg["avg"] or 0, "count": agg["count"] or 0})
