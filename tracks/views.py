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
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.db.models import (
    Max, Exists, OuterRef, Prefetch, Avg, Count, Subquery, F
)
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import ensure_csrf_cookie

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
from playlist.views import _guest_get



##### -------------------- Guest Users Recent List -------------------- #####

GUEST_RECENT_SESSION_KEY = "guest_recent_track_ids"
GUEST_RECENT_LIMIT = 25


def _guest_recent_get(request):
    """Return guest recent track IDs (most recent first)."""
    raw = request.session.get(GUEST_RECENT_SESSION_KEY, [])
    cleaned = []
    for value in raw:
        try:
            cleaned.append(int(value))
        except (TypeError, ValueError):
            continue
    if cleaned != raw:
        request.session[GUEST_RECENT_SESSION_KEY] = cleaned
        request.session.modified = True
    return cleaned


def _guest_recent_push(request, track_id: int):
    """Add a track to the guest recent list (front of list)."""
    ids = _guest_recent_get(request)
    if track_id in ids:
        ids = [tid for tid in ids if tid != track_id]
    ids.insert(0, track_id)
    if len(ids) > GUEST_RECENT_LIMIT:
        ids = ids[:GUEST_RECENT_LIMIT]
    request.session[GUEST_RECENT_SESSION_KEY] = ids
    request.session.modified = True
    return ids


def _guest_recent_clear(request):
    """Clear guest recent list from the session."""
    if request.session.get(GUEST_RECENT_SESSION_KEY) is not None:
        request.session[GUEST_RECENT_SESSION_KEY] = []
        request.session.modified = True

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

        playlist_items_qs = (
            PlaylistItem.objects
            .select_related("track")
            .filter(playlist=playlist)
            .annotate(
                # preferred display name: your custom label, else original track name
                display_name=Coalesce(Subquery(user_label_sq), F("track__name"))
            )
            .order_by("position", "id")
        )

        playlist_items = list(playlist_items_qs)
        in_playlist_ids = {item.track_id for item in playlist_items}

        if playlist_items:
            rated_tracks = annotate_tracks(Track.objects.filter(id__in=in_playlist_ids))
            rating_map = {t.id: t for t in rated_tracks}
            for item in playlist_items:
                rated = rating_map.get(item.track_id)
                if not rated:
                    continue
                item.track.rating_avg = getattr(rated, "rating_avg", 0)
                item.track.rating_count = getattr(rated, "rating_count", 0)


    # ------------------------------- FAVOURITES -------------------------------- #
    fav_rows = (
        Favorite.objects.filter(owner=request.user)
        .order_by("position", "-created_at")
        .values_list("track_id", flat=True)
    )
    fav_id_set = set(fav_rows)

    # Subquery to pull your custom label from any of your albums
    user_label_sq = (
        AlbumTrack.objects
        .filter(album__owner=request.user, track_id=OuterRef("pk"))
        .exclude(custom_name__isnull=True)
        .exclude(custom_name="")
        .values("custom_name")[:1]
    )

    # Fetch tracks in bulk with annotations, then reassemble in fav order
    tracks_by_id = (
        annotate_tracks(Track.objects.filter(id__in=fav_id_set))
        .annotate(display_name=Coalesce(Subquery(user_label_sq), F("name")))
        .in_bulk()
    )

    favorites = []
    for tid in fav_rows:
        t = tracks_by_id.get(tid)
        if not t:
            continue
        t.is_favorited = True
        t.in_playlist = t.id in in_playlist_ids
        t.display_name = getattr(t, "display_name", t.name)
        favorites.append(t)

    annotate_is_in_my_albums(favorites, request.user)


    # ---------------------------- RECENTLY PLAYED ------------------------------ #
    latest_per_track = (
        Listen.objects.filter(user=request.user)
        .values("track")
        .annotate(last_played=Max("played_at"))
        .order_by("-last_played")[:25]
    )

    recent_track_ids = [row["track"] for row in latest_per_track]

    # Subquery: pick your custom name from any of your albums
    user_label_sq = (
        AlbumTrack.objects
        .filter(album__owner=request.user, track_id=OuterRef("pk"))
        .exclude(custom_name__isnull=True)
        .exclude(custom_name="")
        .values("custom_name")[:1]
    )

    recent_tracks_by_id = (
        annotate_tracks(Track.objects.filter(id__in=recent_track_ids))
        .annotate(display_name=Coalesce(Subquery(user_label_sq), F("name")))
        .in_bulk()
    )

    recent = []
    for row in latest_per_track:
        tid = row["track"]
        trk = recent_tracks_by_id.get(tid)
        if not trk:
            continue
        trk.is_favorited = tid in fav_id_set
        trk.in_playlist = tid in in_playlist_ids
        # convenience: always have display_name available
        trk.display_name = getattr(trk, "display_name", trk.name)
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


@ensure_csrf_cookie
def track_list_public(request):
    """
    Public player page for everyone.
    If logged in, also shows Playlists, Favourites, Recently Played.
    """
    # Safe imports here so this function can be pasted anywhere
    from django.shortcuts import render
    from django.db.models import Avg, Count, Exists, F, Max, OuterRef, Subquery, Prefetch
    from django.db.models.functions import Coalesce
    from django.core.exceptions import FieldDoesNotExist
    from tracks.utils import annotate_is_in_my_albums  # keep if you use it below

    # --------------------------- ANONYMOUS: EARLY RETURN --------------------------- #
    if not request.user.is_authenticated:
        guest_ids = _guest_get(request)
        guest_recent_ids = _guest_recent_get(request)

        playlist_map = {t.id: t for t in Track.objects.filter(id__in=guest_ids)}
        guest_tracks = [playlist_map[i] for i in guest_ids if i in playlist_map]

        recent_map = {t.id: t for t in Track.objects.filter(id__in=guest_recent_ids)}
        guest_recent = []
        playlist_id_set = set(guest_ids)
        for tid in guest_recent_ids:
            trk = recent_map.get(tid)
            if not trk:
                continue
            trk.is_favorited = False
            trk.in_playlist = tid in playlist_id_set
            trk.display_name = getattr(trk, "display_name", trk.name)
            guest_recent.append(trk)

        return render(
            request,
            "tracks/track_list_public.html",
            {
                "albums": [],
                "favorites": [],
                "recent": guest_recent,
                "playlist": None,
                "playlist_items": [],
                "guest_tracks": guest_tracks,
                "in_playlist_ids": guest_ids,
            },
        )


    # ----------------------------- PLAYLIST (FIRST) ----------------------------- #
    playlist = None
    playlist_items = []
    in_playlist_ids: set[int] = set()

    playlist, _ = Playlist.objects.get_or_create(owner=request.user, name="My Playlist")

    # Your chosen label from ANY of your albums containing this track
    user_label_sq = (
        AlbumTrack.objects
        .filter(album__owner=request.user, track_id=OuterRef("track_id"))
        .exclude(custom_name__isnull=True)
        .exclude(custom_name="")
        .values("custom_name")[:1]
    )

    playlist_items_qs = (
        PlaylistItem.objects
        .select_related("track")
        .filter(playlist=playlist)
        .annotate(
            # preferred display name: your custom label, else original track name
            display_name=Coalesce(Subquery(user_label_sq), F("track__name"))
        )
        .order_by("position", "id")
    )

    playlist_items = list(playlist_items_qs)
    in_playlist_ids = {item.track_id for item in playlist_items}

    if playlist_items:
        rated_tracks = annotate_tracks(Track.objects.filter(id__in=in_playlist_ids))
        rating_map = {t.id: t for t in rated_tracks}
        for item in playlist_items:
            rated = rating_map.get(item.track_id)
            if not rated:
                continue
            item.track.rating_avg = getattr(rated, "rating_avg", 0)
            item.track.rating_count = getattr(rated, "rating_count", 0)

    # ---------------------------- RECENTLY PLAYED ------------------------------ #
    latest_per_track = (
        Listen.objects.filter(user=request.user)
        .values("track")
        .annotate(last_played=Max("played_at"))
        .order_by("-last_played")[:25]
    )

    recent_track_ids = [row["track"] for row in latest_per_track]

    user_label_sq = (
        AlbumTrack.objects
        .filter(album__owner=request.user, track_id=OuterRef("pk"))
        .exclude(custom_name__isnull=True)
        .exclude(custom_name="")
        .values("custom_name")[:1]
    )

    recent_tracks_by_id = (
        Track.objects.filter(id__in=recent_track_ids)
        .annotate(display_name=Coalesce(Subquery(user_label_sq), F("name")))
        .in_bulk()
    )

    recent = []
    for row in latest_per_track:
        tid = row["track"]
        trk = recent_tracks_by_id.get(tid)
        if not trk:
            continue
        trk.in_playlist = tid in in_playlist_ids
        trk.display_name = getattr(trk, "display_name", trk.name)
        recent.append(trk)

    annotate_is_in_my_albums(recent, request.user)

    # ---------------------------------- ALBUMS --------------------------------- #
    fav_subquery = Favorite.objects.filter(owner=request.user, track=OuterRef("track_id"))

    albums_qs = Album.objects.filter(owner=request.user).prefetch_related(
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

    try:
        Album._meta.get_field("order")
        albums_qs = albums_qs.order_by("order", "id")
    except FieldDoesNotExist:
        albums_qs = albums_qs.order_by("-created_at", "id")

    albums = list(albums_qs)

    for album in albums:
        annotate_is_in_my_albums(album.album_tracks_annotated, request.user, attr="track")
        for at in album.album_tracks_annotated:
            at.track.in_playlist = at.track.id in in_playlist_ids

    # ---------------------- PLAYLIST ROWS THEMSELVES --------------------------- #
    if playlist_items:
        for it in playlist_items:
            it.track.in_playlist = True
            it.track.display_name = it.display_name

    # ------------------------------- RENDER ------------------------------------ #
    return render(
        request,
        "tracks/track_list_public.html",
        {
            "albums": albums,
            "recent": recent,
            "playlist": playlist,
            "playlist_items": playlist_items,
            "in_playlist_ids": list(in_playlist_ids),
        },
    )


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



@require_POST
def clear_recent(request):
    if request.user.is_authenticated:
        Listen.objects.filter(user=request.user).delete()
    else:
        _guest_recent_clear(request)
    return JsonResponse({"ok": True, "msg": "Recent list cleared."})


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
        .order_by("position", "-created_at")   # ⬅️ saved order
    )
    return render(request, "tracks/favorites.html", {"favorites": favs})


@login_required
@require_POST
def favorites_reorder(request):
    import json
    from django.db import transaction

    try:
        payload = json.loads(request.body or "{}")
        order = [int(x) for x in payload.get("order", [])]
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)

    if not order:
        return JsonResponse({"ok": True})

    favs = Favorite.objects.select_related("track").filter(owner=request.user, track_id__in=order)
    by_tid = {f.track_id: f for f in favs}

    pos = 1
    to_update = []
    for tid in order:
        f = by_tid.get(tid)
        if f:
            f.position = pos
            to_update.append(f)
            pos += 1

    with transaction.atomic():
        if to_update:
            Favorite.objects.bulk_update(to_update, ["position"])

    return JsonResponse({"ok": True})




@require_POST
def log_play(request, track_id):
    """Log a listen event (AJAX)."""
    track = get_object_or_404(Track, pk=track_id)
    if request.user.is_authenticated:
        Listen.objects.create(user=request.user, track=track)
    else:
        _guest_recent_push(request, track.id)
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