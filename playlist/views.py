import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Max
from .models import Playlist, PlaylistItem
from tracks.models import Track

def _get_default_playlist(user):
    return Playlist.objects.get_or_create(owner=user, name="My Playlist")[0]

@login_required
@require_GET
def playlist_json(request):
    pl = _get_default_playlist(request.user)
    items = PlaylistItem.objects.select_related("track").filter(playlist=pl).order_by("position", "id")
    data = []
    for it in items:
        t = it.track
        src = ""
        if getattr(t, "audio_file", None):
            try:
                src = t.audio_file.url
            except Exception:
                src = ""
        if not src:
            src = t.source_url or ""
        data.append({
            "id": t.id,
            "name": getattr(t, "name", "Untitled"),
            "src": src,
        })
    return JsonResponse({"tracks": data})



@login_required
@require_POST
def playlist_toggle(request, track_id: int):
    """Toggle a track in/out of the user's default playlist."""
    pl = _get_default_playlist(request.user)
    track = get_object_or_404(Track, pk=track_id)

    item = PlaylistItem.objects.filter(playlist=pl, track=track).order_by("id").first()
    if item:
        item.delete()
        count = PlaylistItem.objects.filter(playlist=pl).count()
        return JsonResponse({
            "ok": True,
            "in_playlist": False,
            "removed": True,
            "count": count,
        })

    # add (append to end)
    max_pos = PlaylistItem.objects.filter(playlist=pl).aggregate(m=Max("position"))["m"]
    pos = (max_pos if max_pos is not None else -1) + 1
    item = PlaylistItem.objects.create(playlist=pl, track=track, position=pos)
    count = PlaylistItem.objects.filter(playlist=pl).count()

    return JsonResponse({
        "ok": True,
        "in_playlist": True,
        "added": True,
        "item_id": item.id,
        "count": count,
    })


    pl = _get_default_playlist(request.user)
    item = get_object_or_404(PlaylistItem, pk=item_id)
    if item.playlist_id != pl.id:
        return HttpResponseForbidden("Not your playlist")
    item.delete()
    return JsonResponse({"ok": True})

@login_required
@require_POST
def playlist_reorder(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        order = payload.get("order", [])
        if not isinstance(order, list):
            return HttpResponseBadRequest("Invalid payload")
    except Exception:
        return HttpResponseBadRequest("Bad JSON")

    pl = _get_default_playlist(request.user)
    # order is a list of PlaylistItem IDs in desired order
    pos = 1
    qs = PlaylistItem.objects.filter(playlist=pl, id__in=order)
    valid_ids = set(qs.values_list("id", flat=True))
    for item_id in order:
        if item_id in valid_ids:
            PlaylistItem.objects.filter(id=item_id, playlist=pl).update(position=pos)
            pos += 1
    return JsonResponse({"ok": True})


@login_required
@require_POST
def playlist_clear(request):
    pl = _get_default_playlist(request.user)
    pl.items.all().delete()
    return JsonResponse({"ok": True})
