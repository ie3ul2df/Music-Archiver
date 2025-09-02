# ----------------------- tracks/views.py ----------------------- #

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from .models import Track, Favorite
from .forms import TrackForm
from album.models import Album, AlbumTrack
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
    # Ensure there's a Default Album for new users
    if not Album.objects.filter(owner=request.user).exists():
        Album.objects.create(owner=request.user, name="Default Album")

    # Prefetch through model and related tracks for efficiency
    albums = (
        Album.objects.filter(owner=request.user)
        .prefetch_related("album_tracks__track")
        .order_by("-created_at")
    )

    storage = user_has_storage_plan(request.user)

    return render(
        request,
        "tracks/track_list.html",
        {
            "albums": albums,
            "has_storage": storage,
        },
    )


@login_required
def album_list(request):
    """Album page: list albums; add album if allowed."""
    albums = Album.objects.filter(owner=request.user).order_by("name")

    if request.method == "POST":
        ok, reason = can_add_album(request.user)
        if not ok:
            messages.error(request, reason)
            return redirect("album_list")

        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Album name is required.")
            return redirect("album_list")

        Album.objects.create(owner=request.user, name=name)
        messages.success(request, "Album created.")
        return redirect("album_list")

    return render(request, "tracks/album_list.html", {"albums": albums})


@login_required
def album_detail(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    if request.method == "POST":
        form = TrackForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            track = form.save()  # already assigns owner
            AlbumTrack.objects.create(album=album, track=track)
            messages.success(request, "Track added to album.")
            return redirect("album_detail", pk=album.pk)
        else:
            messages.error(request, "Fix the errors and try again.")
    else:
        form = TrackForm(owner=request.user)

    tracks = (
        AlbumTrack.objects
        .filter(album=album)
        .select_related("track")
        .order_by("position", "id")
    )

    return render(request, "tracks/album_detail.html", {
        "album": album,
        "tracks": [at.track for at in tracks],  # pass actual Track objects to template
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
        Track.objects.filter(owner=request.user, id__in=id_list).values_list("id", flat=True)
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
    tracks = Track.objects.filter(owner=request.user).order_by("position", "id")
    for t in tracks:
        src = t.audio_file.url if t.audio_file else t.source_url
        if not src:
            continue
        items.append({
            "id": t.id,
            "name": t.name,
            "src": src,
        })
    return JsonResponse({"tracks": items})


@login_required
@require_POST
def ajax_add_album(request):
    """Add a new album (AJAX)."""
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "Album name required."}, status=400)

    album = Album.objects.create(owner=request.user, name=name)
    return JsonResponse({
        "ok": True,
        "id": album.id,
        "name": album.name,
    })


@login_required
@require_POST
def ajax_rename_album(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return JsonResponse({"ok": False, "error": "Name cannot be empty."}, status=400)

    album.name = new_name
    album.save()
    return JsonResponse({"ok": True, "id": album.id, "name": album.name})


@login_required
@require_POST
def ajax_delete_album(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    album.delete()
    return JsonResponse({"ok": True, "id": pk})

@login_required
def play_track(request, pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    track.play_count = (track.play_count or 0) + 1
    track.last_played_at = timezone.now()
    track.save(update_fields=["play_count", "last_played_at"])
    return redirect(track.url)  # simple redirect to the URL you store

@login_required
def recently_played(request):
    items = (
        Track.objects.filter(owner=request.user, last_played_at__isnull=False)
        .order_by("-last_played_at")[:25]
    )
    return render(request, "tracks/recently_played.html", {"tracks": items})


@login_required
def toggle_favorite(request, pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    existing = Favorite.objects.filter(owner=request.user, track=track)
    if existing.exists():
        existing.delete()
        messages.info(request, f"Removed “{track.name}” from favourites.")
    else:
        try:
            Favorite.objects.create(owner=request.user, track=track)
            messages.success(request, f"Added “{track.name}” to favourites.")
        except IntegrityError:
            pass
    return redirect(request.META.get("HTTP_REFERER", "recently_played"))

@login_required
def favorites_list(request):
    favs = Favorite.objects.filter(owner=request.user).select_related("track").order_by("-created_at")
    return render(request, "tracks/favorites.html", {"favorites": favs})