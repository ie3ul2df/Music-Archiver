# ----------------------- tracks/views.py ----------------------- #
import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.http import FileResponse, HttpResponseNotFound, HttpResponseRedirect
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.db.models import (
    Max, Exists, OuterRef, Prefetch, Avg, Count, Subquery, F
)
from django.db.models.functions import Coalesce

from .models import Track, Listen, Favorite
from .forms import TrackForm
from album.models import Album, AlbumTrack
from plans.utils import (
    can_add_track,
    can_add_album,
    can_upload_file,
    user_has_storage_plan,
)
from ratings.utils import annotate_albums, annotate_tracks
from tracks.utils import mark_track_ownership, annotate_is_in_my_albums
from save_system.models import SavedTrack
from playlist.models import Playlist, PlaylistItem
from .models import Listen

##### -------------------- Track List (main tabs UI) -------------------- #####

def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


@login_required
def track_list(request):
    """
    Track list page with four tabs:
      - Albums
      - Favourites
      - Recently Played
      - Playlist (with initial '✓ In' toggle state)
    """
    from tracks.utils import annotate_is_in_my_albums  # local import

    # ----------------------------- PLAYLIST (FIRST) ----------------------------- #
    playlist = None
    playlist_items = []
    in_playlist_ids: set[int] = set()

    if request.user.is_authenticated:
        playlist, _ = Playlist.objects.get_or_create(owner=request.user, name="My Playlist")

        # Your chosen label from ANY of your albums containing this track
        user_label_sq = (
            AlbumTrack.objects
            .filter(album__owner=request.user, track_id=OuterRef("track_id"))
            .exclude(custom_name__isnull=True)
            .exclude(custom_name="")
            .values("custom_name")[:1]
        )

        playlist_items = (
            PlaylistItem.objects
            .select_related("track")
            .filter(playlist=playlist)
            .annotate(
                # preferred display name: your custom label, else original track name
                display_name=Coalesce(Subquery(user_label_sq), F("track__name"))
            )
            .order_by("position", "id")
        )

        in_playlist_ids = set(playlist_items.values_list("track_id", flat=True))


    # ------------------------------- FAVOURITES -------------------------------- #
    fav_ids = list(
        Favorite.objects.filter(owner=request.user).values_list("track_id", flat=True)
    )
    fav_id_set = set(fav_ids)

    favorites_qs = annotate_tracks(Track.objects.filter(id__in=fav_ids))

    fav_order = request.session.get(f"fav_order_{request.user.id}", [])
    if fav_order:
        order_pos = {tid: i for i, tid in enumerate(fav_order)}
        favorites = sorted(favorites_qs, key=lambda t: order_pos.get(t.id, 10**9))
    else:
        favorites = list(favorites_qs.order_by("-created_at")[:25])

    for t in favorites:
        t.is_favorited = True
        t.in_playlist = t.id in in_playlist_ids

    annotate_is_in_my_albums(favorites, request.user)

    # ---------------------------- RECENTLY PLAYED ------------------------------ #
    latest_per_track = (
        Listen.objects.filter(user=request.user)
        .values("track")
        .annotate(last_played=Max("played_at"))
        .order_by("-last_played")[:25]
    )
    recent_track_ids = [row["track"] for row in latest_per_track]

    recent_tracks_by_id = annotate_tracks(
        Track.objects.filter(id__in=recent_track_ids)
    ).in_bulk()

    recent = []
    for row in latest_per_track:
        tid = row["track"]
        trk = recent_tracks_by_id.get(tid)
        if not trk:
            continue
        trk.is_favorited = tid in fav_id_set
        trk.in_playlist = tid in in_playlist_ids
        recent.append(trk)

    annotate_is_in_my_albums(recent, request.user)

    # ---------------------------------- ALBUMS --------------------------------- #
    fav_subquery = Favorite.objects.filter(owner=request.user, track=OuterRef("track_id"))

    albums_qs = annotate_albums(Album.objects.filter(owner=request.user)).prefetch_related(
        Prefetch(
            "album_tracks",
            queryset=(
                AlbumTrack.objects.select_related("track")
                .annotate(
                    is_favorited=Exists(fav_subquery),
                    track_avg=Avg("track__ratings__stars"),
                    track_count=Count("track__ratings", distinct=True),
                )
                .order_by("position", "id")
            ),
            to_attr="album_tracks_annotated",
        )
    )

    albums_qs = (
        albums_qs.order_by("order", "id")
        if _has_field(Album, "order")
        else albums_qs.order_by("-created_at", "id")
    )
    albums = list(albums_qs)

    for album in albums:
        annotate_is_in_my_albums(album.album_tracks_annotated, request.user, attr="track")
        for at in album.album_tracks_annotated:
            at.track.in_playlist = at.track.id in in_playlist_ids

    # ---------------------- PLAYLIST ROWS THEMSELVES --------------------------- #
    if request.user.is_authenticated and playlist_items:
        for it in playlist_items:
            it.track.is_favorited = it.track.id in fav_id_set
            it.track.in_playlist = True
            it.track.display_name = it.display_name

    # ------------------------------- RENDER ------------------------------------ #
    return render(
        request,
        "tracks/track_list.html",
        {
            "albums": albums,
            "favorites": favorites,
            "recent": recent,
            "playlist": playlist,
            "playlist_items": playlist_items,
            "in_playlist_ids": list(in_playlist_ids), 
        },
    )


@login_required
@require_POST
def reorder_tracks(request):
    """Drag-and-drop ordering (global)."""
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


# ---------- Utility Endpoints ----------

def tracks_json(request):
    """Return JSON list of all tracks with playable URLs."""
    data = []
    for t in Track.objects.all().only("id", "name", "audio_file", "source_url"):
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


# ---------- Track Plays / Favorites ----------

@login_required
def play_track(request, pk):
    """Increment play count and redirect to file/URL."""
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    track.play_count = (track.play_count or 0) + 1
    track.last_played_at = timezone.now()
    track.save(update_fields=["play_count", "last_played_at"])
    dest = track.audio_file.url if getattr(track, "audio_file", None) else track.source_url
    return redirect(dest or "track_list")


@login_required
def recently_played(request):
    """Standalone recently played page (not tab)."""
    latest_per_track = (
        Listen.objects.filter(user=request.user)
        .values("track")
        .annotate(last_played=Max("played_at"))
        .order_by("-last_played")[:25]
    )

    track_ids = [item["track"] for item in latest_per_track]
    tracks = Track.objects.in_bulk(track_ids)

    results = [
        {"track": tracks[item["track"]], "last_played": item["last_played"]}
        for item in latest_per_track
        if item["track"] in tracks
    ]
    return render(request, "tracks/recently_played.html", {"results": results})


@login_required
@require_POST
def recent_reorder(request):
    """Save user-defined order of recent tracks in session."""
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
def clear_recent(request):
    if request.method == "POST":
        Listen.objects.filter(user=request.user).delete()
        return JsonResponse({"ok": True, "msg": "Recent list cleared."})
    return JsonResponse({"ok": False, "error": "POST required."}, status=405)


@login_required
@require_POST
def toggle_favorite(request, track_id):
    """Toggle a track in/out of favorites."""
    track = get_object_or_404(Track, pk=track_id)
    qs = Favorite.objects.filter(owner=request.user, track=track)
    if qs.exists():
        qs.delete()
        return JsonResponse({"favorited": False})
    try:
        Favorite.objects.create(owner=request.user, track=track)
    except IntegrityError:
        return JsonResponse({"favorited": True})
    return JsonResponse({"favorited": True})


@login_required
def favorites_list(request):
    favs = (
        Favorite.objects.filter(owner=request.user)
        .select_related("track")
        .order_by("-created_at")
    )
    return render(request, "tracks/favorites.html", {"favorites": favs})


@login_required
@require_POST
def favorites_reorder(request):
    """Save user-defined order of favorites in session."""
    try:
        order = json.loads(request.body or "{}").get("order", [])
        if not isinstance(order, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")
    request.session[f"fav_order_{request.user.id}"] = order
    request.session.modified = True
    return JsonResponse({"ok": True, "scope": "favorites", "order": order})


@login_required
@require_POST
def log_play(request, track_id):
    """Log a listen event (AJAX)."""
    track = get_object_or_404(Track, pk=track_id)
    Listen.objects.create(user=request.user, track=track)
    return JsonResponse({"ok": True})


@login_required
def download_track(request, pk):
    track = get_object_or_404(Track, pk=pk)
    if track.audio_file:
      try:
        return FileResponse(open(track.audio_file.path, "rb"),
                            as_attachment=True,
                            filename=os.path.basename(track.audio_file.name))
      except Exception:
        return HttpResponseNotFound("File not found.")
    if track.source_url:
      return HttpResponseRedirect(track.source_url)
    return HttpResponseNotFound("Nothing to download.")


User = get_user_model()

def user_tracks(request, username):
    author = get_object_or_404(User, username=username)
    qs = annotate_tracks(Track.objects.filter(owner=author).order_by("-created_at"))
    return render(request, "tracks/user_tracks.html", {"author": author, "tracks": qs})


@login_required
@require_POST
def delete_track(request, pk):
    track = get_object_or_404(Track, pk=pk, owner=request.user)
    track.delete()
    return JsonResponse({"ok": True, "id": pk})