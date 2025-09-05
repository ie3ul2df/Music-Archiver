# ----------------------- tracks/views.py ----------------------- #

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Max, Exists, OuterRef, Prefetch
from .models import Track, Listen, Favorite 
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
    Main track list page showing:
    - Favourites (user-scoped; ordered by session order if set, otherwise newest favs first)
    - Recently Played (user-scoped; ordered by session order if set, otherwise most recent first)
    - User's Albums with their tracks (each track annotated with is_favorited)
    """

    # ---------- FAVOURITES ----------
    # Base favourites list (limit to 25 for UI)
    favorites_qs = (
        Favorite.objects
        .filter(owner=request.user)
        .select_related("track")
        .order_by("-created_at")[:25]
    )
    favorites = list(favorites_qs)

    # Apply per-user saved order from session, if available
    fav_order = request.session.get(f"fav_order_{request.user.id}", [])
    if fav_order:
        fav_pos = {tid: i for i, tid in enumerate(fav_order)}
        # Sort by saved position; unknown IDs go to the end (keep stable by created_at fallback)
        favorites.sort(key=lambda f: (fav_pos.get(getattr(f, "track_id", None), 10**9), -f.created_at.timestamp()))

    # ---------- RECENTLY PLAYED ----------
    # Get latest play timestamp per track for this user (limit to 25)
    latest_per_track = (
        Listen.objects
        .filter(user=request.user)
        .values("track")
        .annotate(last_played=Max("played_at"))
        .order_by("-last_played")[:25]
    )

    recent_track_ids = [row["track"] for row in latest_per_track]
    # Fetch Track objects in one query
    tracks_by_id = Track.objects.in_bulk(recent_track_ids)

    # Build a set of ALL favorited track IDs (no limit) to mark hearts in "recent"
    fav_all_ids = set(
        Favorite.objects
        .filter(owner=request.user)
        .values_list("track_id", flat=True)
    )

    # Convert to the structure your template expects and attach is_favorited
    recent = []
    for row in latest_per_track:
        tid = row["track"]
        t = tracks_by_id.get(tid)
        if not t:
            continue
        # attach .is_favorited for template heart state
        t.is_favorited = (tid in fav_all_ids)
        recent.append({"track": t, "last_played": row["last_played"]})

    # Apply saved order from session if present, else keep most-recent-first
    recent_order = request.session.get(f"recent_order_{request.user.id}", [])
    if recent_order:
        rpos = {tid: i for i, tid in enumerate(recent_order)}
        recent.sort(key=lambda r: rpos.get(getattr(r["track"], "id", None), 10**9))
    else:
        recent.sort(key=lambda r: r["last_played"], reverse=True)

    # ---------- ALBUMS (+ annotate is_favorited) ----------
    fav_subquery = Favorite.objects.filter(owner=request.user, track=OuterRef("pk"))
    albums = (
        Album.objects.filter(owner=request.user)
        .prefetch_related(
            Prefetch(
                "album_tracks",
                queryset=AlbumTrack.objects.select_related("track").annotate(
                    is_favorited=Exists(fav_subquery)
                ),
            )
        )
    )

    return render(
        request,
        "tracks/track_list.html",
        {
            "albums": albums,
            "favorites": favorites,
            "recent": recent,
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

    return render(request, "album/album_list.html", {"albums": albums})


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


def tracks_json(request):
    # Make sure each item includes id, name, and a playable URL
    data = []
    for t in Track.objects.all().only("id", "name", "audio_file", "source_url"):
        # Prefer the uploaded file, fall back to an external URL
        src = ""
        if getattr(t, "audio_file", None):
            try:
                src = t.audio_file.url
            except Exception:
                src = ""
        elif t.source_url:
            src = t.source_url
        data.append({"id": t.id, "name": t.name, "src": src})
    return JsonResponse({"tracks": data})


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
    dest = track.audio_file.url if getattr(track, "audio_file", None) else track.source_url
    if not dest:
        # nothing to play; stay on the page or go back
        return redirect("track_list")
    return redirect(dest)


from django.db.models import Max

@login_required
def recently_played(request):
    latest_per_track = (
        Listen.objects.filter(user=request.user)
        .values("track")  # group by track
        .annotate(last_played=Max("played_at"))  # latest play for each
        .order_by("-last_played")[:25]
    )

    # fetch Track objects with timestamp
    track_ids = [item["track"] for item in latest_per_track]
    tracks = Track.objects.in_bulk(track_ids)

    results = [
        {"track": tracks[item["track"]], "last_played": item["last_played"]}
        for item in latest_per_track
    ]

    return render(request, "tracks/recently_played.html", {"results": results})


@require_POST
@login_required
def recent_reorder(request):
    try:
        order = json.loads(request.body or "{}").get("order", [])
        if not isinstance(order, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")
    request.session[f"recent_order_{request.user.id}"] = order
    request.session.modified = True
    return JsonResponse({"ok": True, "scope": "recent", "order": order})



@login_required
@require_POST
def clear_recent(request):
    Listen.objects.filter(user=request.user).delete()
    return JsonResponse({"ok": True})



@require_POST
@login_required
def toggle_favorite(request, track_id):
    # 404 if the track doesn't exist (cleaner than DB FK error)
    track = get_object_or_404(Track, pk=track_id)

    qs = Favorite.objects.filter(owner=request.user, track=track)
    existing = qs.first()

    if existing:
        # Unfavourite
        qs.delete()  # deletes only the matching row(s)
        return JsonResponse({"favorited": False})

    # Favourite (guard against a rare duplicate create)
    try:
        Favorite.objects.create(owner=request.user, track=track)
    except IntegrityError:
        # If a concurrent request created it, just report favorited
        return JsonResponse({"favorited": True})

    return JsonResponse({"favorited": True})


@login_required
def favorites_list(request):
    favs = Favorite.objects.filter(owner=request.user).select_related("track").order_by("-created_at")
    return render(request, "tracks/favorites.html", {"favorites": favs})

@require_POST
@login_required
def favorites_reorder(request):
    try:
        order = json.loads(request.body or "{}").get("order", [])
        if not isinstance(order, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")
    request.session[f"fav_order_{request.user.id}"] = order
    request.session.modified = True
    return JsonResponse({"ok": True, "scope": "favorites", "order": order})

@require_POST
@login_required
def log_play(request, track_id):
    track = get_object_or_404(Track, pk=track_id)
    Listen.objects.create(user=request.user, track=track)
    return JsonResponse({"ok": True})