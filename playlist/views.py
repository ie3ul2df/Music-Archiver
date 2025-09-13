import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db import transaction
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
def playlist_clear(request):
    pl = _get_default_playlist(request.user)
    pl.items.all().delete()
    return JsonResponse({"ok": True})


@login_required
def bulk_add_to_playlist(request):
    """
    Add multiple tracks to the user's default playlist.
    Skips duplicates gracefully.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid method"}, status=405)

    ids = request.POST.get("track_ids", "")
    track_ids = [int(x) for x in ids.split(",") if x.isdigit()]

    playlist, _ = Playlist.objects.get_or_create(owner=request.user, name="My Playlist")

    added, skipped = 0, 0
    for tid in track_ids:
        track = Track.objects.filter(pk=tid).first()
        if not track:
            continue
        if PlaylistItem.objects.filter(playlist=playlist, track=track).exists():
            skipped += 1
        else:
            PlaylistItem.objects.create(
                playlist=playlist,
                track=track,
                position=playlist.items.count()
            )
            added += 1

    return JsonResponse({"ok": True, "added": added, "skipped": skipped})


@login_required
@require_POST
def reorder(request):
    """
    Persist order for the current user's default playlist (or whichever one you're showing).
    Expects JSON: { "order": [playlist_item_id, ...] }
    """
    try:
        payload = json.loads(request.body or "{}")
        order = [int(x) for x in payload.get("order", [])]
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)

    if not order:
        return JsonResponse({"ok": True})

    playlist, _ = Playlist.objects.get_or_create(owner=request.user, name="My Playlist")
    items = PlaylistItem.objects.filter(playlist=playlist, id__in=order)
    by_id = {it.id: it for it in items}

    pos = 1
    to_update = []
    for iid in order:
        it = by_id.get(iid)
        if it:
            it.position = pos
            to_update.append(it)
            pos += 1

    with transaction.atomic():
        if to_update:
            PlaylistItem.objects.bulk_update(to_update, ["position"])

    return JsonResponse({"ok": True})