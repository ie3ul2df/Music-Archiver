# ----------------------- album/views.py ----------------------- #

import json
from django.urls import reverse, NoReverseMatch
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Case, When, IntegerField, F, Q, Count, Avg, Count, Exists, OuterRef, Value, BooleanField, Prefetch, Max
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from .models import Album, AlbumTrack
from .forms import AlbumForm
from tracks.models import Track, Favorite
from tracks.forms import TrackForm
from tracks.utils import mark_track_ownership, annotate_is_in_my_albums, annotate_in_playlist
from ratings.utils import annotate_albums, annotate_tracks
from plans.utils import can_add_album
from save_system.models import SavedTrack
from playlist.models import Playlist, PlaylistItem

# ---------- Helpers ----------

def _can_add_album(user):
    """
    Try to use plans.utils.can_add_album(user).
    Otherwise: free users limited to 1 album.
    """
    try:
        from plans.utils import can_add_album as _cap  
        return _cap(user)
    except Exception:
        count = Album.objects.filter(owner=user).count()
        if count >= 3:
            return False, "Free tier limit reached (3 albums). Upgrade to add more."
        return True, None


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)

def _can_view_album(album, user):
    return (album.is_public or (user.is_authenticated and album.owner_id == user.id))

# -------------- Album fragment view --------------

@login_required
def album_tracks_fragment(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if not (album.owner_id == request.user.id) and not getattr(album, "is_public", False):
        return HttpResponseForbidden("Not allowed.")

    items = (
        AlbumTrack.objects.filter(album=album)
        .select_related("track", "track__owner")
        .annotate(
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("position", "id")
    )

    if request.user.is_authenticated:
        fav_subq = Favorite.objects.filter(owner=request.user, track=OuterRef("track_id"))
        items = items.annotate(is_favorited=Exists(fav_subq))
    else:
        items = items.annotate(is_favorited=Value(False, output_field=BooleanField()))

    # ✅ These ensure _track_card.html has consistent booleans everywhere
    items = list(items)
    annotate_is_in_my_albums(items, request.user, attr="track")
    annotate_in_playlist(items, request.user, attr="track")

    return render(
        request,
        "album/_album_tracks_fragment.html",
        {"album": album, "items": items, "is_owner": album.owner_id == request.user.id},
    )

# ---------------------- Album functions ---------------------- #
# ---------------------- Album functions ---------------------- #
# ---------------------- Album functions ---------------------- #


@login_required
def album_list(request):
    """
    List current user's albums (ordered if field available) + ratings; create on POST.
    Also provides Saved Albums & Saved Tracks for the tabs on album_list.html.
    """
    # --- Create album (UNCHANGED) ---
    if request.method == "POST":
        ok, reason = can_add_album(request.user)
        if not ok:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": reason}, status=400)
            messages.error(request, reason)
            return redirect("album:album_list")

        name = (request.POST.get("name") or "").strip()
        if not name:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": "Album name is required."}, status=400)
            messages.error(request, "Album name is required.")
            return redirect("album:album_list")

        album = Album.objects.create(owner=request.user, name=name)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True,
                "id": album.id,
                "name": album.name,
                "detail_url": reverse("album:album_detail", args=[album.pk]),
            })
        else:
            messages.success(request, "Album created.")
            return redirect("album:album_list")

    # --- Your albums (order + ratings) ---
    qs = Album.objects.filter(owner=request.user)
    if _has_field(Album, "order"):
        qs = qs.order_by("order", "id")
    else:
        qs = qs.order_by("-created_at", "id")

    # Prefetch album tracks with per-track annotations for _track_card.html
    fav_subq = Favorite.objects.filter(owner=request.user, track=OuterRef("track_id"))
    items_qs = (
        AlbumTrack.objects.select_related("track", "track__owner")
        .annotate(
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
            is_favorited=Exists(fav_subq),
        )
        .order_by("position", "id")
    )
    qs = qs.prefetch_related(Prefetch("album_tracks", queryset=items_qs))

    # Album-level annotations (avg/count on Album itself)
    albums = list(annotate_albums(qs))

    # Ensure each Track inside those albums has consistent flags used by _track_card.html
    for alb in albums:
        ats = list(getattr(alb, "album_tracks").all())
        # already has: at.is_favorited, at.track_avg, at.track_count (from items_qs)
        # add:
        annotate_is_in_my_albums(ats, request.user, attr="track")  # sets at.track.is_in_my_albums
        annotate_in_playlist(ats, request.user, attr="track")      # sets at.track.in_playlist

    # --- Saved items for tabs (kept intact, but optimized and flagged) ---
    try:
        from save_system.models import SavedAlbum, SavedTrack

        saved_albums = (
            SavedAlbum.objects
            .filter(owner=request.user)
            .select_related("original_album", "original_album__owner")
            .order_by("-saved_at")
        )

        # We want _track_card.html to behave the same for saved tracks
        fav_track_subq = Favorite.objects.filter(
            owner=request.user, track=OuterRef("original_track_id")
        )

        saved_tracks = (
            SavedTrack.objects
            .filter(owner=request.user)
            .select_related("original_track", "original_track__owner", "album")
            .annotate(is_favorited=Exists(fav_track_subq))  # attach fav on SavedTrack row
            .order_by("-saved_at")
        )

        # annotate flags on the track objects (original_track) so templates can use them directly
        tracks_only = [s.original_track for s in saved_tracks if s.original_track]
        annotate_is_in_my_albums(tracks_only, request.user)  # sets .is_in_my_albums
        annotate_in_playlist(tracks_only, request.user)      # sets .in_playlist

    except Exception:
        saved_albums = []
        saved_tracks = []

    return render(
        request,
        "album/album_list.html",
        {
            "albums": albums,
            "saved_albums": saved_albums,
            "saved_tracks": saved_tracks,
        },
    )


def _maybe_reverse(name, *args, **kwargs):
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return None


@login_required
def unified_search(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"albums_html": "", "tracks_html": ""})

    user = request.user

    # ✓ / ➕ playlist state
    try:
        playlist, _ = Playlist.objects.get_or_create(owner=user, name="My Playlist")
        in_playlist_ids = set(
            PlaylistItem.objects.filter(playlist=playlist).values_list("track_id", flat=True)
        )
    except Exception:
        in_playlist_ids = set()

    # favorite subquery for track annotations
    fav_sub = Favorite.objects.filter(owner=user, track_id=OuterRef("track_id"))

    # ---- ALBUMS: prefetch annotated AlbumTracks -> album.album_tracks_annotated ----
    at_qs = (
        AlbumTrack.objects.select_related("track", "track__owner")
        .annotate(
            is_favorited=Exists(fav_sub),
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("position", "id")
    )

    albums = (
        Album.objects.filter(owner=user, name__icontains=q)
        .prefetch_related(Prefetch("album_tracks", queryset=at_qs, to_attr="album_tracks_annotated"))
        .order_by("name")[:20]
    )

    # add in_playlist flag to prefetched tracks
    for a in albums:
        for at in getattr(a, "album_tracks_annotated", []):
            at.track.in_playlist = (at.track_id in in_playlist_ids)

    # render full album cards with URLs passed in (NEVER None — provide fallbacks)
    album_cards = []
    for a in albums:
        # detail URL (used for fallbacks)
        detail_url = (
            _maybe_reverse("album:album_detail", a.pk)
            or _maybe_reverse("album:detail", a.pk)
            or f"/album/{a.pk}/"
        )
        base = detail_url.rstrip("/")

        rename_url = (
            _maybe_reverse("album:album_rename", a.pk)
            or _maybe_reverse("album:album_update", a.pk)
            or _maybe_reverse("album:rename", a.pk)
            or _maybe_reverse("album:update", a.pk)
            or f"{base}/rename/"
        )

        toggle_visibility_url = (
            _maybe_reverse("album:album_toggle_visibility", a.pk)
            or _maybe_reverse("album:toggle_visibility", a.pk)
            or _maybe_reverse("album:toggle", a.pk)
            or f"{base}/toggle-visibility/"
        )

        delete_url = (
            _maybe_reverse("album:album_delete", a.pk)
            or _maybe_reverse("album:delete", a.pk)
            or f"{base}/delete/"
        )


        album_cards.append(
            render_to_string(
                "album/_album_card.html",
                {
                    "album": a,
                    "rename_url": rename_url,
                    "toggle_visibility_url": toggle_visibility_url,
                    "delete_url": delete_url,
                    "owner_url": None,          
                },
                request=request,
            )
        )

    albums_html = "".join(album_cards)

    # ---- TRACKS: render _track_card.html for matches inside user's albums ----
    at_hits = (
        AlbumTrack.objects.select_related("album", "track", "track__owner")
        .filter(album__owner=user, track__name__icontains=q)
        .annotate(
            is_favorited=Exists(fav_sub),
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("album__name", "position", "id")[:50]
    )

    tracks_html = "".join(
        render_to_string(
            "tracks/_track_card.html",
            {
                "track": at.track,
                "album": at.album,
                "album_item_id": at.id,
                "is_owner": (at.album.owner_id == user.id),
                "is_favorited": bool(at.is_favorited),
                "in_playlist": (at.track_id in in_playlist_ids),
                "avg": at.track_avg or 0,
                "count": at.track_count or 0,
                "show_checkbox": True,
                "at": at,
            },
            request=request,
        )
        for at in at_hits
    )

    return JsonResponse({"albums_html": albums_html, "tracks_html": tracks_html})


@login_required
@require_POST
def ajax_add_album(request):
    """Add a new album (AJAX-only). Enforces plan limits and sets order/position if present."""
    ok, reason = can_add_album(request.user)
    if not ok:
        return JsonResponse({"ok": False, "error": reason or "Album limit reached."}, status=403)

    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "Album name required."}, status=400)

    album = Album(owner=request.user, name=name)

    # Put new album at the end if you have ordering fields
    if _has_field(Album, "order"):
        last = Album.objects.filter(owner=request.user).order_by("-order", "-id").first()
        album.order = (last.order + 1) if last and last.order is not None else 0
    elif _has_field(Album, "position"):
        last = Album.objects.filter(owner=request.user).order_by("-position", "-id").first()
        album.position = (last.position + 1) if last and last.position is not None else 0

    album.save()

    detail_url = reverse("album:album_detail", args=[album.pk])
    rename_url = reverse("album:ajax_rename_album", args=[album.pk])
    toggle_url = reverse("album:toggle_album_visibility", args=[album.pk])
    delete_url = reverse("album:ajax_delete_album", args=[album.pk])

    return JsonResponse(
        {
            "ok": True,
            "id": album.id,
            "name": album.name,
            "detail_url": detail_url,
            "edit_url": rename_url,
            "toggle_url": toggle_url,
            "delete_url": delete_url,
            "is_public": album.is_public,
        }
    )


@login_required
@require_POST
def ajax_rename_album(request, pk):
    """Rename an album (AJAX-only)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return JsonResponse({"ok": False, "error": "Name cannot be empty."}, status=400)
    if new_name != album.name:
        album.name = new_name
        album.save(update_fields=["name"])
    return JsonResponse({"ok": True, "id": album.id, "name": album.name})


@login_required
@require_POST
def ajax_delete_album(request, pk):
    """Delete an album (AJAX-only)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    album.delete()
    return JsonResponse({"ok": True, "id": pk})


@login_required
def album_detail(request, pk):
    """
    Show album with tracks.
    - Owner: can edit (add tracks, delete)
    - Visitor: can only view if album is public
    """

    album = get_object_or_404(
        Album.objects.all(),
        Q(pk=pk) & (Q(owner=request.user) | Q(is_public=True))
    )

    # Annotate ratings for the album
    album = annotate_albums(Album.objects.filter(pk=album.pk)).first()
    is_owner = album.owner == request.user

    # --- Handle POST (only add-track form here; other actions handled by AJAX views) ---
    if is_owner and request.method == "POST":
        if "name" in request.POST and ("source_url" in request.POST or "audio_file" in request.FILES):
            form = TrackForm(request.POST, request.FILES, owner=request.user)
            if form.is_valid():
                track = form.save()
                last_pos = AlbumTrack.objects.filter(album=album).aggregate(m=Max("position"))["m"] or -1
                pos = last_pos + 1
                AlbumTrack.objects.create(album=album, track=track, position=pos)
                messages.success(request, "Track added to album.")
                return redirect("album:album_detail", pk=album.pk)
            messages.error(request, "Fix the errors and try again.")
        else:
            # Not an add-track POST → let AJAX endpoints handle it
            form = TrackForm(owner=request.user)
    else:
        form = TrackForm(owner=request.user) if is_owner else None

    # --- Tracks with annotations ---
    items_qs  = (
        AlbumTrack.objects.filter(album=album)
        .select_related("track")
        .annotate(
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
            is_favorited=Exists(
                Favorite.objects.filter(owner=request.user, track_id=OuterRef("track_id"))
            ),
        )
        .order_by("position", "id")
    )
    
    # Evaluate once so downstream helpers (and the template include) see the
    # annotated attributes.
    items = list(items_qs)

    mark_track_ownership(items, request.user)
    annotate_is_in_my_albums(items, request.user, attr="track")

    # mark whether each track is already saved in one of the user's albums
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            SavedTrack.objects.filter(
                owner=request.user,
                original_track__in=[it.track for it in items]
            ).values_list("original_track_id", flat=True)
        )
    for it in items:
        it.track.is_in_my_albums = it.track.id in saved_ids

    # The shared album card partial looks for `album.album_tracks_annotated`
    # (populated by Prefetch in other views). Mirror that behaviour here so
    # the track cards receive the annotated AlbumTrack objects with the
    # rating aggregates, ensuring the star buttons highlight correctly.
    album.album_tracks_annotated = items

    # Template choice
    template_name = "album/album_detail.html" if is_owner else "album/public_album_detail.html"

    # URLs for _album_card.html include
    context = {
        "album": album,
        "items": items,
        "form": form,
        "is_owner": is_owner,
        "has_storage": True,  # TODO: connect with storage plans
        "owner_url": reverse("user_tracks", args=[album.owner.username]),
        "rename_url": reverse("album:ajax_rename_album", args=[album.pk]),
        "toggle_visibility_url": reverse("album:toggle_album_visibility", args=[album.pk]),
        "delete_url": reverse("album:ajax_delete_album", args=[album.pk]),
        "delete_redirect_url": reverse("album:album_list"),
    }

    return render(request, template_name, context)


def public_album_detail(request, slug):
    """Public album detail page with ratings and tracks."""
    album = get_object_or_404(Album, slug=slug, is_public=True)
    album = annotate_albums(Album.objects.filter(pk=album.pk)).first()

    tracks = (
        AlbumTrack.objects.filter(album=album)
        .select_related("track")
        .annotate(
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("id")
    )
    mark_track_ownership(tracks, request.user)

    # ✅ mark saved status for logged-in users
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            SavedTrack.objects.filter(
                owner=request.user,
                original_track__in=[it.track for it in tracks]
            ).values_list("original_track_id", flat=True)
        )
    for it in tracks:
        it.track.is_in_my_albums = it.track.id in saved_ids

    return render(
        request,
        "album/public_album_detail.html",
        {
            "album": album,
            "tracks": tracks,
        },
    )


@login_required
@require_POST
def album_add_track(request, pk):
    """Add existing track to album (if not already present)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    tid = request.POST.get("track_id")
    if not tid:
        messages.error(request, "Select a track to add.")
        return redirect("album:album_detail", pk=pk)

    track = get_object_or_404(Track, pk=tid, owner=request.user)

    if AlbumTrack.objects.filter(album=album, track=track).exists():
        messages.info(request, "Track is already in this album.")
        return redirect("album:album_detail", pk=pk)

    last = AlbumTrack.objects.filter(album=album).order_by("-position").first()
    pos = (last.position + 1) if last else 0
    AlbumTrack.objects.create(album=album, track=track, position=pos)
    messages.success(request, "Added to album.")
    return redirect("album:album_detail", pk=pk)


@login_required
@require_POST
def album_remove_track(request, pk, item_id):
    """Remove a specific track from the album."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album=album)
    item.delete()
    messages.success(request, "Removed from album.")
    return redirect("album:album_detail", pk=pk)


@login_required
def toggle_album_visibility(request, pk):
    """Toggle album public/private."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    album.is_public = not album.is_public
    album.save(update_fields=["is_public"])
    state = "public" if album.is_public else "private"
    messages.success(request, f"“{album.name}” is now {state}.")
    return redirect("album:album_detail", pk=album.pk)


@login_required
def track_create(request):
    if request.method == "POST":
        form = TrackForm(request.user, request.POST)
        if form.is_valid():
            track = form.save()
            messages.success(request, f'Added “{track.title}”.')
            return redirect("recently_played")
    else:
        form = TrackForm(request.user)
    return render(request, "tracks/track_form.html", {"form": form})


@login_required
@require_POST
def album_rename_track(request, pk, item_id):
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album=album)

    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "Track name cannot be empty."}, status=400)
        messages.error(request, "Track name cannot be empty.")
        return redirect("album:album_detail", pk=pk)

    is_owner = (item.track.owner_id == request.user.id)

    with transaction.atomic():
        if is_owner:
            # Global rename for your track
            item.track.name = new_name
            item.track.save(update_fields=["name"])

            # Optional: clear any stale custom names you might have for this track
            # AlbumTrack.objects.filter(album__owner=request.user, track=item.track)\
            #     .update(custom_name=None)
        else:
            # Set on this item…
            item.custom_name = new_name
            item.save(update_fields=["custom_name"])
            # …and propagate to all your albums containing the same original track
            AlbumTrack.objects.filter(
                album__owner=request.user,
                track=item.track,
            ).update(custom_name=new_name)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "album_item_id": item.id,
            "name": item.custom_name or item.track.name,  # the label to show
            "scope": "track",          # tells the UI to update all cards for this track
            "track_id": item.track_id, # so JS can locate them
        })

    messages.success(request, f'Name updated to “{new_name}”.')
    return redirect("album:album_detail", pk=pk)


@login_required
@require_POST
def album_detach_track(request, pk, item_id):
    """⛔ Remove a specific track from the album (does NOT delete the track)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album=album)
    track = item.track

    # Delete the AlbumTrack entry
    item.delete()

    # Also clean up SavedTrack snapshot if it exists for this album+track
    from save_system.models import SavedTrack
    SavedTrack.objects.filter(owner=request.user, album=album, original_track=track).delete()

    messages.success(request, "Removed from album.")
    return redirect("album:album_detail", pk=pk)


@login_required
@require_POST
def album_bulk_detach(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    # Accept JSON body or form-encoded items[]
    items = []
    try:
        if (request.META.get("CONTENT_TYPE") or "").startswith("application/json"):
            payload = json.loads(request.body.decode("utf-8") or "{}")
            items = payload.get("items", [])
        else:
            items = request.POST.getlist("items[]") or request.POST.getlist("items")
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    # Normalize to ints
    try:
        item_ids = [int(x) for x in items]
    except Exception:
        return HttpResponseBadRequest("Invalid item IDs")

    qs = AlbumTrack.objects.filter(album=album, id__in=item_ids)
    to_remove = list(qs.values_list("id", flat=True))

    with transaction.atomic():
        qs.delete()
        # re-pack positions to keep list tidy (optional)
        remaining = list(AlbumTrack.objects.filter(album=album).order_by("position", "id"))
        for i, at in enumerate(remaining):
            if at.position != i:
                AlbumTrack.objects.filter(pk=at.pk).update(position=i)

    return JsonResponse({"ok": True, "removed": to_remove, "album_id": album.id})


@login_required
@require_POST
def ajax_reorder_albums(request):
    """
    Save user's album list order. Expects JSON: { "order": [album_id, ...] }
    """
    try:
        payload = json.loads(request.body or "{}")
        order = [int(x) for x in payload.get("order", [])]
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)

    if not order:
        return JsonResponse({"ok": True})

    albums = Album.objects.filter(owner=request.user, id__in=order)
    by_id = {a.id: a for a in albums}

    pos = 1
    to_update = []
    for aid in order:
        a = by_id.get(aid)
        if a:
            a.order = pos
            to_update.append(a)
            pos += 1

    with transaction.atomic():
        if to_update:
            Album.objects.bulk_update(to_update, ["order"])

    return JsonResponse({"ok": True})


@login_required
@require_POST
def album_reorder_tracks(request, pk):
    """
    Reorder tracks within a specific album.
    Expects JSON: { "order": [albumtrack_id, ...] }  (AlbumTrack IDs, not Track IDs)
    """
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    try:
        payload = json.loads(request.body or "{}")
        incoming = [int(x) for x in payload.get("order", [])]
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)

    # Current rows in stable order
    current_qs = AlbumTrack.objects.filter(album=album).order_by("position", "id")
    all_ids = list(current_qs.values_list("id", flat=True))
    if not all_ids:
        return JsonResponse({"ok": True})

    # Build final ordered list: first the incoming order (validated), then leftovers
    seen = set()
    final_ids = []
    for aid in incoming:
        if aid in all_ids and aid not in seen:
            final_ids.append(aid)
            seen.add(aid)
    for aid in all_ids:
        if aid not in seen:
            final_ids.append(aid)

    # Map each AlbumTrack id -> new position 1..n
    mapping = {aid: idx + 1 for idx, aid in enumerate(final_ids)}

    # Two-phase, collision-free update:
    with transaction.atomic():
        # Phase 1: bump everything away so UNIQUE(album, position) never collides
        AlbumTrack.objects.filter(album=album).update(position=F("position") + 1_000_000)

        # Phase 2: assign the real positions in one go with CASE
        whens = [When(id=aid, then=Value(pos)) for aid, pos in mapping.items()]
        AlbumTrack.objects.filter(album=album, id__in=mapping.keys()).update(
            position=Case(*whens, output_field=IntegerField())
        )

    return JsonResponse({"ok": True})


