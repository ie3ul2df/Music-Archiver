from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.db.models import F
from .models import Track
from .forms import TrackForm
import json


# ---------- Helpers for limits / storage (safe fallbacks if plans.utils isn't present) ----------
def _can_add_track(user):
    """
    Uses plans.utils.can_add_track if available; otherwise enforces a free limit of 10 tracks.
    Returns (ok: bool, reason: Optional[str]).
    """
    try:
        from plans.utils import can_add_track as _cat  # type: ignore
        ok, reason = _cat(user)
        return ok, reason
    except Exception:
        # Fallback: free tier → 10 tracks max
        count = Track.objects.filter(user=user).count()
        if count >= 10:
            return False, "Free tier limit reached (10 tracks). Upgrade a plan to add more."
        return True, None


def _can_upload_file(user, size_bytes: int):
    """
    Uses plans.utils.can_upload_file if available; otherwise allow uploads (no quota)
    so we don't break existing behaviour.
    Returns (ok: bool, reason: Optional[str]).
    """
    try:
        from plans.utils import can_upload_file as _cuf  # type: ignore
        ok, reason = _cuf(user, size_bytes)
        return ok, reason
    except Exception:
        return True, None  # permissive fallback


def _has_field(model_cls, field_name: str) -> bool:
    return any(f.name == field_name for f in model_cls._meta.fields)


# ---------- Views ----------
@login_required
def track_list(request):
    """Show all tracks belonging to the logged-in user (ordered if `position` field exists)."""
    qs = Track.objects.filter(user=request.user)
    if _has_field(Track, "position"):
        tracks = qs.order_by("position", "id")
    else:
        # Fallback to most-recent-first if no explicit ordering field
        tracks = qs.order_by("-created_at")
    return render(request, "tracks/track_list.html", {"tracks": tracks})


@login_required
def track_create(request):
    """Add a new track (link or file upload). Enforces free-tier limits; storage quota if available."""
    if request.method == "POST":
        ok, reason = _can_add_track(request.user)
        if not ok:
            messages.error(request, reason or "You can't add more tracks.")
            return redirect("track_list")

        form = TrackForm(request.POST, request.FILES)
        if form.is_valid():
            track = form.save(commit=False)
            track.user = request.user

            # If uploading a file, enforce storage quota (when plans.utils is present).
            upload = getattr(track, "audio_file", None)
            if upload:
                ok, reason = _can_upload_file(request.user, getattr(upload, "size", 0) or 0)
                if not ok:
                    messages.error(request, reason or "Not enough storage to upload this file.")
                    return redirect("track_list")

            # If a 'position' field exists, append to the end.
            if _has_field(Track, "position"):
                last = (
                    Track.objects.filter(user=request.user)
                    .order_by("-position")
                    .first()
                )
                track.position = (last.position + 1) if last else 0

            track.save()
            messages.success(request, "Track added successfully!")
            return redirect("track_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TrackForm()

    return render(request, "tracks/track_form.html", {"form": form})


@login_required
def track_update(request, pk):
    """Edit a track"""
    track = get_object_or_404(Track, pk=pk, user=request.user)
    if request.method == "POST":
        form = TrackForm(request.POST, request.FILES, instance=track)
        if form.is_valid():
            updated = form.save(commit=False)

            # If switching to an upload or changing the file, re-check storage
            upload = getattr(updated, "audio_file", None)
            if upload and hasattr(upload, "size"):
                ok, reason = _can_upload_file(request.user, upload.size)
                if not ok:
                    messages.error(request, reason or "Not enough storage for this file.")
                    return redirect("track_list")

            updated.save()
            messages.success(request, "Track updated successfully!")
            return redirect("track_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TrackForm(instance=track)
    return render(request, "tracks/track_form.html", {"form": form})


@login_required
def track_delete(request, pk):
    """Delete a track"""
    track = get_object_or_404(Track, pk=pk, user=request.user)
    if request.method == "POST":
        track.delete()
        messages.success(request, "Track deleted!")
        return redirect("track_list")
    return render(request, "tracks/track_confirm_delete.html", {"track": track})


@login_required
@require_POST
def reorder_tracks(request):
    """
    Drag-and-drop ordering endpoint.
    Accepts JSON: { "order": [track_id_1, track_id_2, ...] }
    Requires a 'position' field on Track; otherwise returns a gentle error.
    """
    if not _has_field(Track, "position"):
        return JsonResponse(
            {"ok": False, "error": "Ordering is not enabled for tracks."},
            status=400,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
        id_list = data.get("order", [])
        if not isinstance(id_list, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload.")

    # Only allow reordering of the current user's tracks
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
    Lightweight JSON feed for a frontend media player.
    Returns user's tracks in current order with a playable src (file or link).
    """
    qs = Track.objects.filter(user=request.user)
    if _has_field(Track, "position"):
        qs = qs.order_by("position", "id")
    else:
        qs = qs.order_by("-created_at")

    items = []
    for t in qs:
        src = None
        # Prefer uploaded file if present
        if hasattr(t, "audio_file") and t.audio_file:
            try:
                src = t.audio_file.url
            except Exception:
                src = None
        # Fallback to link field(s)
        if not src:
            # Common field name in your forms/models has been 'source_url'
            if hasattr(t, "source_url") and t.source_url:
                src = t.source_url
            # If you used another name like 'url' or 'link', try them too:
            elif hasattr(t, "url") and t.url:
                src = t.url
            elif hasattr(t, "link") and t.link:
                src = t.link

        if not src:
            # Skip tracks without a resolvable source
            continue

        items.append({
            "id": t.id,
            "name": t.name,
            "src": src,
            "type": "file" if (hasattr(t, "audio_file") and t.audio_file) else "link",
        })

    return JsonResponse({"tracks": items})
