from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import F
from .models import Playlist, PlaylistTrack
from .forms import PlaylistForm
from tracks.models import Track
import json


# ---------- Helpers for limits / safe fallbacks ----------
def _can_add_playlist(user):
    """
    Uses plans.utils.can_add_playlist if available; otherwise enforces a free limit of 1 playlist.
    Returns (ok: bool, reason: Optional[str]).
    """
    try:
        from plans.utils import can_add_playlist as _cap  # type: ignore
        ok, reason = _cap(user)
        return ok, reason
    except Exception:
        count = Playlist.objects.filter(user=user).count()
        if count >= 1:
            return False, "Free tier limit reached (1 playlist). Upgrade a plan to add more."
        return True, None


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


# ---------- Views ----------
@login_required
def playlist_list(request):
    """List all playlists for the logged-in user (ordered if `position` exists)."""
    qs = Playlist.objects.filter(user=request.user)
    if _has_field(Playlist, "position"):
        playlists = qs.order_by("position", "id")
    else:
        playlists = qs.order_by("-created_at")
    return render(request, "playlist/playlist_list.html", {"playlists": playlists})


@login_required
def playlist_create(request):
    """Create a new playlist (tracks are managed on the detail page)."""
    if request.method == "POST":
        ok, reason = _can_add_playlist(request.user)
        if not ok:
            messages.error(request, reason or "You can't create more playlists.")
            return redirect("playlist_list")

        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user

            # If playlist has a sortable 'position' field, append at end.
            if _has_field(Playlist, "position"):
                last = (
                    Playlist.objects.filter(user=request.user)
                    .order_by("-position")
                    .first()
                )
                playlist.position = (last.position + 1) if last else 0

            playlist.save()
            messages.success(request, "Playlist created successfully!")
            return redirect("playlist_detail", pk=playlist.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PlaylistForm()
    return render(request, "playlist/playlist_form.html", {"form": form})


@login_required
def playlist_update(request, pk):
    """
    Edit playlist details (name/description).
    NOTE: Track membership & order are edited on the detail page with drag-and-drop.
    """
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    if request.method == "POST":
        # Ensure the form excludes M2M 'tracks' because we use a through model with extra fields.
        form = PlaylistForm(request.POST, instance=playlist)
        if form.is_valid():
            form.save()
            messages.success(request, "Playlist updated successfully!")
            return redirect("playlist_detail", pk=playlist.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PlaylistForm(instance=playlist)
    return render(request, "playlist/playlist_form.html", {"form": form, "playlist": playlist})


@login_required
def playlist_detail(request, pk):
    """
    Show a single playlist with its ordered items and allow adding tracks.
    Drag-and-drop reordering is handled via `playlist_reorder`.
    """
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    items = (
        PlaylistTrack.objects.filter(playlist=playlist)
        .select_related("track")
        .order_by("position", "id")
    )
    user_tracks = Track.objects.filter(user=request.user).order_by("name")
    return render(
        request,
        "playlist/playlist_detail.html",
        {"playlist": playlist, "items": items, "user_tracks": user_tracks},
    )


@login_required
@require_POST
def playlist_add_track(request, pk):
    """Add a user's track to the playlist at the end (if not already present)."""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    tid = request.POST.get("track_id")
    if not tid:
        messages.error(request, "Select a track to add.")
        return redirect("playlist_detail", pk=pk)

    track = get_object_or_404(Track, pk=tid, user=request.user)

    # If it already exists, do nothing.
    exists = PlaylistTrack.objects.filter(playlist=playlist, track=track).exists()
    if exists:
        messages.info(request, "Track is already in this playlist.")
        return redirect("playlist_detail", pk=pk)

    last = (
        PlaylistTrack.objects.filter(playlist=playlist)
        .order_by("-position")
        .first()
    )
    pos = (last.position + 1) if last else 0
    PlaylistTrack.objects.create(playlist=playlist, track=track, position=pos)
    messages.success(request, "Added to playlist.")
    return redirect("playlist_detail", pk=pk)


@login_required
@require_POST
def playlist_remove_track(request, pk, item_id):
    """Remove a specific PlaylistTrack row."""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    item = get_object_or_404(PlaylistTrack, pk=item_id, playlist=playlist)
    item.delete()
    messages.success(request, "Removed from playlist.")
    return redirect("playlist_detail", pk=pk)


@login_required
@require_POST
def playlist_reorder(request, pk):
    """
    Reorder tracks inside a playlist by updating PlaylistTrack.position.
    Expects JSON: { "order": [playlisttrack_id_1, playlisttrack_id_2, ...] }
    """
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    # Only reorder items that belong to the current playlist
    valid_ids = set(
        PlaylistTrack.objects.filter(playlist=playlist, id__in=id_list)
        .values_list("id", flat=True)
    )

    pos = 0
    for iid in id_list:
        if iid in valid_ids:
            PlaylistTrack.objects.filter(id=iid).update(position=pos)
            pos += 1

    return JsonResponse({"ok": True, "updated": list(valid_ids)})


@login_required
@require_POST
def playlists_reorder(request):
    """
    Reorder the user's playlists (if Playlist has a `position` field).
    Expects JSON: { "order": [playlist_id_1, playlist_id_2, ...] }
    """
    if not _has_field(Playlist, "position"):
        return JsonResponse(
            {"ok": False, "error": "Ordering is not enabled for playlists."},
            status=400,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    user_ids = set(
        Playlist.objects.filter(user=request.user, id__in=id_list)
        .values_list("id", flat=True)
    )

    pos = 0
    for pid in id_list:
        if pid in user_ids:
            Playlist.objects.filter(id=pid).update(position=pos)
            pos += 1

    return JsonResponse({"ok": True, "updated": list(user_ids)})


@login_required
def playlist_delete(request, pk):
    """Delete a playlist"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    if request.method == "POST":
        playlist.delete()
        messages.success(request, "Playlist deleted!")
        return redirect("playlist_list")
    return render(request, "playlist/playlist_confirm_delete.html", {"playlist": playlist})
