from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db import IntegrityError
from django.db.models import Max
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.template.loader import render_to_string

from album.models import Album, AlbumTrack
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
        try:
            import json
            album_id = json.loads(request.body.decode("utf-8")).get("album_id")
        except Exception:
            pass

    if not album_id:
        return HttpResponseBadRequest("album_id is required.")

    # must be YOUR album
    album = get_object_or_404(Album, pk=album_id, owner=request.user)

    # 1) Create/keep the snapshot record
    name_snapshot = getattr(track, "name", None) or getattr(track, "title", None) or str(track)
    try:
        saved_obj, saved_created = SavedTrack.objects.get_or_create(
            owner=request.user,
            original_track=track,
            album=album,
            defaults={"name_snapshot": name_snapshot},
        )
    except IntegrityError:
        saved_created = False

    # 2) ALSO attach to the album so it appears on album_detail
    try:
        # next position at the end
        next_pos = (AlbumTrack.objects.filter(album=album)
                    .aggregate(mp=Max("position"))["mp"] or 0) + 1

        _, attached_created = AlbumTrack.objects.get_or_create(
            album=album,
            track=track,
            defaults={"position": next_pos},
        )
    except IntegrityError:
        attached_created = False

    return JsonResponse({
        "ok": True,
        "created": saved_created,      # snapshot created?
        "attached": attached_created,  # album link created?
    })



# @login_required
# def bulk_save_tracks(request):
#     if request.method != "POST":
#         return redirect("album:album_list")

#     track_ids = [int(x) for x in request.POST.get("track_ids", "").split(",") if x.isdigit()]
#     album_id = request.POST.get("album_id")
#     if not track_ids or not album_id:
#         if request.headers.get("x-requested-with") == "XMLHttpRequest":
#             return JsonResponse({"ok": False, "error": "Missing tracks or album."}, status=400)
#         messages.error(request, "Missing tracks or album.")
#         return redirect("album:album_list")

#     album = get_object_or_404(Album, pk=album_id, owner=request.user)

#     added, skipped = 0, 0
#     for tid in track_ids:
#         try:
#             track = Track.objects.get(pk=tid)
#         except Track.DoesNotExist:
#             skipped += 1
#             continue

#         if AlbumTrack.objects.filter(album=album, track=track).exists():
#             skipped += 1
#             continue

#         AlbumTrack.objects.create(album=album, track=track)
#         added += 1

#     # --- Return JSON if AJAX ---
#     if request.headers.get("x-requested-with") == "XMLHttpRequest":
#         return JsonResponse({"ok": True, "added": added, "skipped": skipped, "album": album.name})

#     # --- Fallback: normal Django messages + redirect ---
#     if added and skipped:
#         messages.success(request, f"Saved {added} track(s); {skipped} already there.")
#     elif added:
#         messages.success(request, f"Saved {added} track(s).")
#     else:
#         messages.info(request, f"All selected tracks were already in “{album.name}”.")
#     return redirect("album:album_list")




@login_required
def bulk_save_tracks(request):
    if request.method != "POST":
        return redirect("album:album_list")

    track_ids = [int(x) for x in request.POST.get("track_ids", "").split(",") if x.isdigit()]
    album_id = request.POST.get("album_id")
    album = get_object_or_404(Album, pk=album_id, owner=request.user)

    added, skipped = [], []
    for tid in track_ids:
        try:
            track = Track.objects.get(pk=tid)
        except Track.DoesNotExist:
            skipped.append(tid)
            continue

        if AlbumTrack.objects.filter(album=album, track=track).exists():
            skipped.append(tid)
            continue

        at = AlbumTrack.objects.create(album=album, track=track)
        added.append(at)

    # If AJAX, send JSON + rendered HTML
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = "".join(
            render_to_string("tracks/_track_card.html", {
                "track": at.track,
                "album": album,
                "album_item_id": at.id,
                "is_owner": True,
                "show_checkbox": True,
                "is_favorited": False,
                "in_playlist": False,
                "avg": 0,
                "count": 0,
            }, request=request)
            for at in added
        )
        return JsonResponse({
            "ok": True,
            "added": len(added),
            "skipped": len(skipped),
            "html": html,
            "album_id": album.id,
        })

    # fallback redirect
    messages.success(request, f"Saved {len(added)} track(s); {len(skipped)} skipped.")
    return redirect("album:album_list")
