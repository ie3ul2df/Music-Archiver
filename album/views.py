# ----------------------- album/views.py ----------------------- #

from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Album, AlbumTrack
from .forms import AlbumForm
from tracks.models import Track
from tracks.forms import TrackForm  # ← TrackForm lives in tracks app
import json


# ---------- Helpers for limits / safe fallbacks ----------
def _can_add_album(user):
    """
    Uses plans.utils.can_add_album if available; otherwise enforces a free limit of 1 album.
    Returns (ok: bool, reason: Optional[str]).
    """
    try:
        from plans.utils import can_add_album as _cap  # type: ignore
        return _cap(user)
    except Exception:
        # Album model uses `owner` (not `user`)
        count = Album.objects.filter(owner=user).count()
        if count >= 1:
            return False, "Free tier limit reached (1 album). Upgrade a plan to add more."
        return True, None


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


# ---------- Views ----------
@login_required
def album_list(request):
    """List all albums for the logged-in user (ordered if `position` exists)."""
    qs = Album.objects.filter(owner=request.user)
    if _has_field(Album, "position"):
        albums = qs.order_by("position", "id")
    else:
        albums = qs.order_by("-created_at")
    return render(request, "album/album_list.html", {"albums": albums})


@login_required
def album_create(request):
    """Create a new album."""
    if request.method == "POST":
        ok, reason = _can_add_album(request.user)
        if not ok:
            messages.error(request, reason or "You can't create more albums.")
            return redirect("album_list")

        form = AlbumForm(request.POST)
        if form.is_valid():
            album = form.save(commit=False)
            album.owner = request.user  # ← Album has `owner`

            # If album has a sortable 'position' field, append at end.
            if _has_field(Album, "position"):
                last = (
                    Album.objects.filter(owner=request.user)
                    .order_by("-position")
                    .first()
                )
                album.position = (last.position + 1) if last else 0

            album.save()
            messages.success(request, "Album created successfully!")
            return redirect("album_detail", pk=album.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AlbumForm()
    return render(request, "album/album_form.html", {"form": form})


@login_required
def album_update(request, pk):
    """Rename/update an album (name/description only)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    if request.method == "POST":
        form = AlbumForm(request.POST, instance=album)
        if form.is_valid():
            form.save()
            messages.success(request, "Album updated successfully!")
            return redirect("album_detail", pk=album.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AlbumForm(instance=album)
    return render(request, "album/album_form.html", {"form": form, "album": album})


@login_required
def album_detail(request, pk):
    """Show a single album with its ordered tracks, allow adding, and support drag reordering."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    if request.method == "POST":
        form = TrackForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            track = form.save()
            last = AlbumTrack.objects.filter(album=album).order_by("-position").first()
            pos = (last.position + 1) if last else 0
            AlbumTrack.objects.create(album=album, track=track, position=pos)
            messages.success(request, "Track added to album.")
            return redirect("album_detail", pk=album.pk)
        else:
            messages.error(request, "Fix the errors and try again.")
    else:
        form = TrackForm(owner=request.user)

    items = (
        AlbumTrack.objects.filter(album=album)
        .select_related("track")
        .order_by("position", "id")
    )

    return render(
        request,
        "album/album_detail.html",
        {
            "album": album,
            "items": items,       # AlbumTrack objects for drag reorder
            "form": form,
            "has_storage": True,  # or use user_has_storage_plan(request.user)
        },
    )


@login_required
@require_POST
def album_add_track(request, pk):
    """Add a user's track to the album at the end (if not already present)."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    tid = request.POST.get("track_id")
    if not tid:
        messages.error(request, "Select a track to add.")
        return redirect("album_detail", pk=pk)

    track = get_object_or_404(Track, pk=tid, owner=request.user)

    # If it already exists, do nothing.
    if AlbumTrack.objects.filter(album=album, track=track).exists():
        messages.info(request, "Track is already in this album.")
        return redirect("album_detail", pk=pk)

    last = AlbumTrack.objects.filter(album=album).order_by("-position").first()
    pos = (last.position + 1) if last else 0
    AlbumTrack.objects.create(album=album, track=track, position=pos)  # ← named args
    messages.success(request, "Added to album.")
    return redirect("album_detail", pk=pk)


@login_required
@require_POST
def album_remove_track(request, pk, item_id):
    """Remove a specific track from the album."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album=album)  # ← kwarg
    item.delete()
    messages.success(request, "Removed from album.")
    return redirect("album_detail", pk=pk)



@login_required
@require_POST
def album_reorder_tracks(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = [int(x) for x in data.get("order", [])]
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    items = list(AlbumTrack.objects.filter(album=album, id__in=id_list))

    item_map = {i.id: i for i in items}

    with transaction.atomic():
        for pos, iid in enumerate(id_list):
            if iid in item_map:
                item_map[iid].position = pos
                item_map[iid].save(update_fields=["position"])

    return JsonResponse({"ok": True, "updated": id_list})


@login_required
@require_POST
def albums_reorder(request):
    """Reorder the user's albums (if Album has a `position` field)."""
    if not _has_field(Album, "position"):
        return JsonResponse(
            {"ok": False, "error": "Ordering is not enabled for albums."}, status=400
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
        id_list = [int(x) for x in id_list]
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    user_ids = set(
        Album.objects.filter(owner=request.user, id__in=id_list).values_list("id", flat=True)
    )

    pos = 0
    for aid in id_list:
        if aid in user_ids:
            Album.objects.filter(id=aid).update(position=pos)
            pos += 1

    return JsonResponse({"ok": True, "updated": list(user_ids)})


@login_required
def album_delete(request, pk):
    """Delete an album."""
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    if request.method == "POST":
        album.delete()
        messages.success(request, "Album deleted!")
        return redirect("album_list")
    return render(request, "album/album_confirm_delete.html", {"album": album})


def public_album_detail(request, slug):
    album = get_object_or_404(Album, slug=slug, is_public=True)
    tracks = (
        AlbumTrack.objects.select_related("track")
        .filter(album=album)
        .order_by("id")
    )
    return render(request, "album/public_album_detail.html", {"album": album, "tracks": tracks})


@login_required
def toggle_album_visibility(request, pk):
    album = get_object_or_404(Album, pk=pk, owner=request.user)
    album.is_public = not album.is_public
    album.save()
    state = "public" if album.is_public else "private"
    messages.success(request, f"“{album.name}” is now {state}.")
    return redirect("album_detail", pk=album.pk)


# (Optional) Track creation kept here for convenience, but consider moving to tracks/views.py
@login_required
def track_create(request):
    if request.method == "POST":
        form = TrackForm(request.user, request.POST)
        if form.is_valid():
            track = form.save()
            messages.success(request, f'Added “{track.title}”.')
            return redirect("recently_played")  # or your preferred page
    else:
        form = TrackForm(request.user)
    return render(request, "tracks/track_form.html", {"form": form})
