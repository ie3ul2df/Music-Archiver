# ----------------------- album/views.py ----------------------- #

import json
from django.urls import reverse
from django.db import transaction
from django.db.models import Case, When, IntegerField, F, Q, Count, Avg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Album, AlbumTrack
from .forms import AlbumForm
from tracks.models import Track
from tracks.forms import TrackForm
from ratings.utils import annotate_albums, annotate_tracks
from plans.utils import can_add_album


# ---------- Helpers ----------

def _can_add_album(user):
    """
    Try to use plans.utils.can_add_album(user).
    Otherwise: free users limited to 1 album.
    """
    try:
        from plans.utils import can_add_album as _cap  # type: ignore
        return _cap(user)
    except Exception:
        count = Album.objects.filter(owner=user).count()
        if count >= 1:
            return False, "Free tier limit reached (1 album). Upgrade to add more."
        return True, None


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


# ---------- Views ----------

@login_required
def album_list(request):
    """
    List current user's albums (ordered if field available) + ratings; create on POST.
    Also provides Saved Albums & Saved Tracks for the tabs on album_list.html.
    """
    # Handle create
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

    # Your albums (with ratings)
    qs = Album.objects.filter(owner=request.user)
    if _has_field(Album, "order"):
        qs = qs.order_by("order", "id")
    else:
        qs = qs.order_by("-created_at", "id")
    albums = annotate_albums(qs)  # adds rating_avg & rating_count

    # Saved items for tabs (lazy import to avoid circular if app not installed yet)
    try:
        from save_system.models import SavedAlbum, SavedTrack

        saved_albums = (
            SavedAlbum.objects
            .filter(owner=request.user)
            .select_related("original_album")
            .order_by("-saved_at")
        )
        saved_tracks = (
            SavedTrack.objects
            .filter(owner=request.user)
            .select_related("original_track", "album")
            .order_by("-saved_at")
        )
    except Exception:
        # save_system not installed yet; keep page working
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


@login_required
def album_detail(request, pk):
    """Show album with tracks.
    - Owner: can edit (add tracks, reorder, delete)
    - Visitor: can only view if album is public
    """

    album = get_object_or_404(
        Album.objects.all(),
        Q(pk=pk) & (Q(owner=request.user) | Q(is_public=True))
    )

    # Annotate ratings
    album = annotate_albums(Album.objects.filter(pk=album.pk)).first()
    is_owner = album.owner == request.user

    # Handle POST only if user owns the album
    if is_owner and request.method == "POST":
        form = TrackForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            track = form.save()
            last = AlbumTrack.objects.filter(album=album).order_by("-position").first()
            pos = (last.position + 1) if last else 0
            AlbumTrack.objects.create(album=album, track=track, position=pos)
            messages.success(request, "Track added to album.")
            return redirect("album:album_detail", pk=album.pk)
        messages.error(request, "Fix the errors and try again.")
    else:
        form = TrackForm(owner=request.user) if is_owner else None

    # Tracks with rating annotations
    items = (
        AlbumTrack.objects.filter(album=album)
        .select_related("track")
        .annotate(
            track_avg=Avg("track__ratings__stars"),
            track_count=Count("track__ratings", distinct=True),
        )
        .order_by("position", "id")
    )

    # Choose template
    template_name = "album/album_detail.html" if is_owner else "album/public_album_detail.html"

    return render(
        request,
        template_name,
        {
            "album": album,
            "items": items,
            "form": form,            # None for visitors
            "is_owner": is_owner,
            "has_storage": True,     # TODO: integrate with storage plans
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
@require_POST
def album_reorder_tracks(request, pk):
    """Reorder tracks inside one album without violating (album_id, position) uniqueness."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    # Parse payload
    try:
      data = json.loads(request.body.decode("utf-8"))
      id_list = [int(x) for x in data.get("order", [])]
    except Exception:
      return HttpResponseBadRequest("Invalid JSON payload.")

    # Get ALL AlbumTrack ids for this album in current order
    all_ids = list(
        AlbumTrack.objects
        .filter(album=album)
        .order_by("position", "id")
        .values_list("id", flat=True)
    )
    if not all_ids:
        return JsonResponse({"ok": True, "updated": []})

    # Build a final order that contains every item exactly once:
    # 1) keep ids provided by the client (that belong to this album), in that order
    # 2) append any missing ids in their current order
    seen = set()
    final_order = []
    for iid in id_list:
        if iid in all_ids and iid not in seen:
            final_order.append(iid)
            seen.add(iid)
    for iid in all_ids:
        if iid not in seen:
            final_order.append(iid)

    # Two-phase update using a large offset to avoid UNIQUE collisions in SQLite
    with transaction.atomic():
        # Move ALL rows for this album far away
        AlbumTrack.objects.filter(album=album).update(position=F("position") + 1_000_000)

        # Assign final positions with a CASE
        case = Case(
            *[When(id=iid, then=pos) for pos, iid in enumerate(final_order)],
            output_field=IntegerField(),
        )
        AlbumTrack.objects.filter(album=album, id__in=final_order).update(position=case)

    return JsonResponse({"ok": True, "updated": final_order})



@login_required
@require_POST
def albums_reorder(request):
    if not _has_field(Album, "order"):
        return JsonResponse({"ok": False, "error": "Ordering is not enabled for albums."}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = [int(x) for x in data.get("order", [])]
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    user_qs = Album.objects.filter(owner=request.user)
    user_ids = list(user_qs.values_list("id", flat=True))
    if not user_ids:
        return JsonResponse({"ok": True, "updated": []})

    # Build final ids: keep client order that belongs to the user, then append missing
    seen = set()
    final_ids = []
    for aid in id_list:
        if aid in user_ids and aid not in seen:
            final_ids.append(aid); seen.add(aid)
    for aid in user_ids:
        if aid not in seen:
            final_ids.append(aid)

    with transaction.atomic():
        user_qs.update(order=F("order") + 1_000_000)
        case = Case(
            *[When(id=aid, then=pos) for pos, aid in enumerate(final_ids)],
            output_field=IntegerField(),
        )
        user_qs.filter(id__in=final_ids).update(order=case)

    return JsonResponse({"ok": True, "updated": final_ids})




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
    return render(request, "album/public_album_detail.html", {"album": album, "tracks": tracks})


@login_required
def toggle_album_visibility(request, pk):
    """Toggle album public/private."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    album.is_public = not album.is_public
    album.save(update_fields=["is_public"])
    state = "public" if album.is_public else "private"
    messages.success(request, f"“{album.name}” is now {state}.")
    return redirect("album:album_detail", pk=album.pk)


# (Optional) Track creation shortcut (consider moving to tracks/views.py)
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
def album_search(request):
    q = request.GET.get("q", "").strip()
    albums = Album.objects.filter(owner=request.user)
    if q:
        albums = albums.filter(name__icontains=q)

    albums = annotate_albums(albums)  # ⭐ add rating fields if available

    results = []
    for a in albums:
        results.append({
            "id": a.id,
            "name": a.name,
            "is_public": a.is_public,
            "detail_url": reverse("album:album_detail", args=[a.id]),
            "toggle_url": reverse("album:toggle_album_visibility", args=[a.id]), 
            "edit_url": reverse("album:ajax_rename_album", args=[a.id]),
        })
    return JsonResponse({"results": results})


@login_required
@require_POST
def album_rename_track(request, pk, item_id):
    """Rename a specific track in the album."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album=album)

    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        messages.error(request, "Track name cannot be empty.")
        return redirect("album:album_detail", pk=pk)

    item.track.name = new_name
    item.track.save(update_fields=["name"])
    messages.success(request, f'Track renamed to “{new_name}”.')
    return redirect("album:album_detail", pk=pk)











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
    return JsonResponse({"ok": True, "id": album.id, "name": album.name, "detail_url": detail_url})

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