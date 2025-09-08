from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db import IntegrityError
from django.utils.decorators import method_decorator

from album.models import Album
from tracks.models import Track
from .models import SavedAlbum, SavedTrack

def _is_public_album(album):
    """
    Try to detect "public" per your codebase.
    You have public routes and toggles, so the model likely has a flag/field.
    We check common variants and default to True if the field isn't present.
    """
    for attr in ("is_public", "public"):
        if hasattr(album, attr):
            return bool(getattr(album, attr))
    # Some projects use a 'visibility' field with 'public'/'private'
    if hasattr(album, "visibility"):
        val = getattr(album, "visibility")
        try:
            return str(val).lower() == "public"
        except Exception:
            return False
    # Fallback: allow (you already expose only public albums in UI)
    return True

@login_required
@require_POST
def save_album(request, pk):
    album = get_object_or_404(Album, pk=pk)

    # prevent saving your own album (you already own it)
    if getattr(album, "owner_id", None) == request.user.id:
        return JsonResponse({"ok": False, "error": "You already own this album."}, status=400)

    if not _is_public_album(album):
        return HttpResponseForbidden("Album is not public.")

    name_snapshot = getattr(album, "name", str(album)) or ""
    description_snapshot = ""
    for attr in ("description", "desc", "summary"):
        if hasattr(album, attr):
            description_snapshot = getattr(album, attr) or ""
            break

    try:
        obj, created = SavedAlbum.objects.get_or_create(
            owner=request.user,
            original_album=album,
            defaults={
                "name_snapshot": name_snapshot,
                "description_snapshot": description_snapshot,
            },
        )
        return JsonResponse({"ok": True, "created": created})
    except IntegrityError:
        return JsonResponse({"ok": True, "created": False})

@login_required
@require_POST
def save_track(request, pk):
    track = get_object_or_404(Track, pk=pk)

    # album_id can come from standard form submit or fetch(body)
    album_id = request.POST.get("album_id")
    if not album_id and request.body:
        # attempt JSON
        try:
            import json
            album_id = json.loads(request.body.decode("utf-8")).get("album_id")
        except Exception:
            pass

    if not album_id:
        return HttpResponseBadRequest("album_id is required.")

    album = get_object_or_404(Album, pk=album_id, owner=request.user)

    # optional: prevent saving your own track (up to you)
    # if getattr(track, "owner_id", None) == request.user.id:
    #     return JsonResponse({"ok": False, "error": "You already own this track."}, status=400)

    name_snapshot = getattr(track, "name", None) or getattr(track, "title", None) or str(track)

    try:
        obj, created = SavedTrack.objects.get_or_create(
            owner=request.user,
            original_track=track,
            album=album,
            defaults={"name_snapshot": name_snapshot},
        )
        return JsonResponse({"ok": True, "created": created})
    except IntegrityError:
        return JsonResponse({"ok": True, "created": False})
