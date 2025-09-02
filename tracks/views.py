# tracks/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages

from .models import Track
from .forms import TrackForm
from album.models import Album
from plans.utils import (
    can_add_track,
    can_add_album,
    can_upload_file,
    user_has_storage_plan,
)

import json


@login_required
def track_list(request):
    """
    Music Player page:
    - Sticky player on top (template)
    - Albums listed underneath with their tracks
    """
    # Ensure there's a Default Album for new users (so they always see one)
    if not Album.objects.filter(user=request.user).exists():
        Album.objects.create(user=request.user, name="Default Album")

    albums = Album.objects.filter(user=request.user).prefetch_related("tracks")
    storage = user_has_storage_plan(request.user)
    return render(request, "tracks/track_list.html", {
        "albums": albums,
        "has_storage": storage,
    })


@login_required
def album_list(request):
    """Album page: list albums; add album if allowed."""
    albums = Album.objects.filter(user=request.user).order_by("name")

    if request.method == "POST":
        ok, reason = can_add_album(request.user)
        if not ok:
            messages.error(request, reason)
            return redirect("album_list")

        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Album name is required.")
            return redirect("album_list")

        Album.objects.create(user=request.user, name=name)
        messages.success(request, "Album created.")
        return redirect("album_list")

    return render(request, "tracks/album_list.html", {"albums": albums})


@login_required
def album_detail(request, pk):
    """
    Show an album and allow adding tracks into it (respect plan limits).
    """
    album = get_object_or_404(Album, pk=pk, user=request.user)
    if request.method == "POST":
        # Gate by plan
        ok, reason = can_add_track(request.user, album)
        if not ok:
            messages.error(request, reason)
            return redirect("album_detail", pk=album.pk)

        form = TrackForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            t = form.save(commit=False)
            t.user = request.user
            t.album = album  # force into this album

            # If uploading a file, check storage quota
            if t.audio_file and hasattr(t.audio_file, "size"):
                ok, reason = can_upload_file(request.user, t.audio_file.size)
                if not ok:
                    messages.error(request, reason)
                    return redirect("album_detail", pk=album.pk)

            last = (Track.objects
                    .filter(user=request.user, album=album)
                    .order_by("-position")
                    .first())
            t.position = (last.position + 1) if last else 0
            t.save()
            messages.success(request, "Track added to album.")
            return redirect("album_detail", pk=album.pk)
        else:
            messages.error(request, "Fix the errors and try again.")
    else:
        form = TrackForm(user=request.user)

    tracks = Track.objects.filter(user=request.user, album=album).order_by("position", "id")
    return render(request, "tracks/album_detail.html", {
        "album": album,
        "tracks": tracks,
        "form": form,
        "has_storage": user_has_storage_plan(request.user),
    })


@login_required
@require_POST
def reorder_tracks(request):
    """
    Drag-and-drop ordering (global). Accepts JSON: { "order": [track_id, ...] }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    user_ids = list(
        Track.objects.filter(user=request.user, id__in=id_list).values_list("id", flat=True)
    )

    pos = 0
    for tid in id_list:
        if tid in user_ids:
            Track.objects.filter(id=tid).update(position=pos)
            pos += 1

    return JsonResponse({"ok": True, "updated": user_ids})


@login_required
def tracks_json(request):
    """
    JSON feed for the sticky player (all user's tracks, ordered).
    """
    items = []
    for t in Track.objects.filter(user=request.user).order_by("position", "id"):
        src = t.audio_file.url if t.audio_file else t.source_url
        if not src:
            continue
        items.append({
            "id": t.id,
            "name": t.name,
            "album": t.album.name if t.album else "",
            "src": src,
            "type": "file" if t.audio_file else "link",
        })
    return JsonResponse({"tracks": items})

@login_required
@require_POST
def ajax_add_album(request):
    """Add a new album (AJAX)."""
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "Album name required."}, status=400)

    album = Album.objects.create(user=request.user, name=name)
    return JsonResponse({
        "ok": True,
        "id": album.id,
        "name": album.name,
    })


@login_required
@require_POST
def ajax_rename_album(request, pk):
    album = get_object_or_404(Album, pk=pk, user=request.user)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return JsonResponse({"ok": False, "error": "Name cannot be empty."}, status=400)

    album.name = new_name
    album.save()
    return JsonResponse({"ok": True, "id": album.id, "name": album.name})


@login_required
@require_POST
def ajax_delete_album(request, pk):
    album = get_object_or_404(Album, pk=pk, user=request.user)
    album.delete()
    return JsonResponse({"ok": True, "id": pk})