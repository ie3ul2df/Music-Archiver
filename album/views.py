from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Album as Album, AlbumTrack as AlbumTrack
from .forms import AlbumForm as AlbumForm
from tracks.models import Track
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
        count = Album.objects.filter(user=user).count()
        if count >= 1:
            return False, "Free tier limit reached (1 album). Upgrade a plan to add more."
        return True, None


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


# ---------- Views ----------
@login_required
def album_list(request):
    """List all albums for the logged-in user (ordered if `position` exists)."""
    qs = Album.objects.filter(user=request.user)
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
            album.user = request.user

            # If album has a sortable 'position' field, append at end.
            if _has_field(Album, "position"):
                last = (
                    Album.objects.filter(user=request.user)
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
    album = get_object_or_404(Album, pk=pk, user=request.user)
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
    """Show a single album with its ordered tracks and allow adding tracks."""
    album = get_object_or_404(Album, pk=pk, user=request.user)
    items = (
        AlbumTrack.objects.filter(album)  
        .select_related("track")
        .order_by("position", "id")
    )
    user_tracks = Track.objects.filter(user=request.user).order_by("name")
    return render(
        request,
        "album/album_detail.html",
        {"album": album, "items": items, "user_tracks": user_tracks},
    )


@login_required
@require_POST
def album_add_track(request, pk):
    """Add a user's track to the album at the end (if not already present)."""
    album = get_object_or_404(Album, pk=pk, user=request.user)
    tid = request.POST.get("track_id")
    if not tid:
        messages.error(request, "Select a track to add.")
        return redirect("album_detail", pk=pk)

    track = get_object_or_404(Track, pk=tid, user=request.user)

    # If it already exists, do nothing.
    exists = AlbumTrack.objects.filter(album, track=track).exists()
    if exists:
        messages.info(request, "Track is already in this album.")
        return redirect("album_detail", pk=pk)

    last = AlbumTrack.objects.filter(album).order_by("-position").first()
    pos = (last.position + 1) if last else 0
    AlbumTrack.objects.create(album, track=track, position=pos)
    messages.success(request, "Added to album.")
    return redirect("album_detail", pk=pk)


@login_required
@require_POST
def album_remove_track(request, pk, item_id):
    """Remove a specific track from the album."""
    album = get_object_or_404(Album, pk=pk, user=request.user)
    item = get_object_or_404(AlbumTrack, pk=item_id, album)
    item.delete()
    messages.success(request, "Removed from album.")
    return redirect("album_detail", pk=pk)


@login_required
@require_POST
def album_reorder_tracks(request, pk):
    """Reorder tracks inside an album."""
    album = get_object_or_404(Album, pk=pk, user=request.user)

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    # Only reorder items that belong to this album
    valid_ids = set(
        AlbumTrack.objects.filter(album, id__in=id_list).values_list("id", flat=True)
    )

    pos = 0
    for iid in id_list:
        if iid in valid_ids:
            AlbumTrack.objects.filter(id=iid).update(position=pos)
            pos += 1

    return JsonResponse({"ok": True, "updated": list(valid_ids)})


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
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    user_ids = set(
        Album.objects.filter(user=request.user, id__in=id_list).values_list("id", flat=True)
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
    album = get_object_or_404(Album, pk=pk, user=request.user)
    if request.method == "POST":
        album.delete()
        messages.success(request, "Album deleted!")
        return redirect("album_list")
    return render(request, "album/album_confirm_delete.html", {"album": album})
