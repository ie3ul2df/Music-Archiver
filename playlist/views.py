import json
from typing import Iterable, List

from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from tracks.models import Track

from .models import Playlist, PlaylistItem

# -------------------------- Helpers --------------------------

SESSION_KEY = "guest_playlist_ids"


def _get_default_playlist(user) -> Playlist:
    return Playlist.objects.get_or_create(owner=user, name="My Playlist")[0]


def _session_get_list(request) -> List[int]:
    """
    Get the guest playlist as a list of track IDs, preserving order.
    """
    lst = request.session.get(SESSION_KEY, [])
    # normalize to ints (ignore garbage)
    cleaned = []
    for x in lst:
        try:
            cleaned.append(int(x))
        except Exception:
            continue
    if cleaned != lst:
        request.session[SESSION_KEY] = cleaned
        request.session.modified = True
    return cleaned


def _session_set_list(request, track_ids: Iterable[int]) -> None:
    request.session[SESSION_KEY] = list(track_ids)
    request.session.modified = True


def _session_toggle_track(request, track_id: int) -> bool:
    """
    Toggle track in the guest playlist.
    Returns True if now IN playlist, False if removed.
    """
    lst = _session_get_list(request)
    if track_id in lst:
        lst = [t for t in lst if t != track_id]
        _session_set_list(request, lst)
        return False
    lst.append(track_id)
    _session_set_list(request, lst)
    return True


def _session_bulk_add(request, track_ids: Iterable[int]) -> tuple[int, int]:
    """
    Add multiple tracks to the session playlist; skip duplicates.
    Returns (added_count, skipped_count).
    """
    existing = _session_get_list(request)
    s = set(existing)
    added = 0
    for tid in track_ids:
        if tid in s:
            continue
        existing.append(tid)
        s.add(tid)
        added += 1
    _session_set_list(request, existing)
    skipped = len(track_ids) - added
    return added, skipped


def _session_reorder(request, order_ids: List[int]) -> None:
    """
    Reorder the session playlist according to the list of track IDs provided.
    Any tracks not in 'order_ids' are kept after, in their previous relative order.
    """
    cur = _session_get_list(request)
    want = [tid for tid in order_ids if tid in cur]
    # keep leftovers (present in cur but not in want) preserving old order
    leftovers = [tid for tid in cur if tid not in set(want)]
    _session_set_list(request, want + leftovers)


# -------------------------- Views --------------------------


@require_GET
@ensure_csrf_cookie  # ensures guests receive a CSRF cookie for subsequent POSTs
def playlist_json(request):
    """
    Return the current playlist (tracks with playable src) for:
      - authenticated users: DB playlist
      - guests: session playlist (track IDs stored in session)
    """
    data = []

    if request.user.is_authenticated:
        pl = _get_default_playlist(request.user)
        items = (
            PlaylistItem.objects.select_related("track")
            .filter(playlist=pl)
            .order_by("position", "id")
        )
        for it in items:
            t = it.track
            src = ""
            if getattr(t, "audio_file", None):
                try:
                    src = t.audio_file.url
                except Exception:
                    src = ""
            if not src:
                src = t.source_url or ""
            if not src:
                continue
            data.append(
                {"id": t.id, "name": getattr(t, "name", "Untitled"), "src": src}
            )
        return JsonResponse({"tracks": data})

    # Guest: build from session IDs
    ids = _session_get_list(request)
    if not ids:
        return JsonResponse({"tracks": []})

    # Preserve order in response
    tracks_by_id = (
        Track.objects.filter(id__in=ids)
        .only("id", "name", "audio_file", "source_url")
        .in_bulk(ids)
    )
    for tid in ids:
        t = tracks_by_id.get(tid)
        if not t:
            continue
        src = ""
        if getattr(t, "audio_file", None):
            try:
                src = t.audio_file.url
            except Exception:
                src = ""
        if not src:
            src = t.source_url or ""
        if not src:
            continue
        data.append({"id": t.id, "name": getattr(t, "name", "Untitled"), "src": src})
    return JsonResponse({"tracks": data})


@require_POST
def playlist_toggle(request, track_id: int):
    """
    Toggle a track in/out of the default playlist.
      - Auth: DB PlaylistItem
      - Guest: session list
    """
    # Validate track exists (both auth & guest)
    track = get_object_or_404(Track, pk=track_id)

    if request.user.is_authenticated:
        pl = _get_default_playlist(request.user)
        existing = (
            PlaylistItem.objects.filter(playlist=pl, track=track).order_by("id").first()
        )
        if existing:
            existing.delete()
            count = PlaylistItem.objects.filter(playlist=pl).count()
            return JsonResponse(
                {"ok": True, "in_playlist": False, "removed": True, "count": count}
            )

        # append to end
        max_pos = PlaylistItem.objects.filter(playlist=pl).aggregate(m=Max("position"))[
            "m"
        ]
        pos = (max_pos if max_pos is not None else -1) + 1
        item = PlaylistItem.objects.create(playlist=pl, track=track, position=pos)
        count = PlaylistItem.objects.filter(playlist=pl).count()
        return JsonResponse(
            {
                "ok": True,
                "in_playlist": True,
                "added": True,
                "item_id": item.id,
                "count": count,
            }
        )

    # Guest
    now_in = _session_toggle_track(request, track_id)
    count = len(_session_get_list(request))
    return JsonResponse({"ok": True, "in_playlist": now_in, "count": count})


@require_POST
def playlist_clear(request):
    """
    Clear the playlist.
      - Auth: delete items in DB
      - Guest: clear session list
    """
    if request.user.is_authenticated:
        pl = _get_default_playlist(request.user)
        pl.items.all().delete()
    else:
        _session_set_list(request, [])
    return JsonResponse({"ok": True})


@require_POST
def bulk_add_to_playlist(request):
    """
    Add multiple tracks to the playlist.
    Request:
      - form-encoded or JSON
      - "track_ids": "1,2,3" OR JSON body { "track_ids": [1,2,3] }
    Skips duplicates; returns { ok, added, skipped }.
    """
    # Parse ids from form or JSON
    track_ids: List[int] = []
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body or "{}")
            raw = payload.get("track_ids", [])
            if isinstance(raw, str):
                track_ids = [int(x) for x in raw.split(",") if str(x).isdigit()]
            else:
                track_ids = [int(x) for x in raw if str(x).isdigit()]
        except Exception:
            return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)
    else:
        ids = request.POST.get("track_ids", "")
        track_ids = [int(x) for x in ids.split(",") if x.isdigit()]

    # Strip unknown tracks silently
    valid_ids = set(Track.objects.filter(id__in=track_ids).values_list("id", flat=True))
    track_ids = [tid for tid in track_ids if tid in valid_ids]

    if not track_ids:
        return JsonResponse({"ok": True, "added": 0, "skipped": 0})

    if request.user.is_authenticated:
        playlist = _get_default_playlist(request.user)
        existing = set(
            PlaylistItem.objects.filter(
                playlist=playlist, track_id__in=track_ids
            ).values_list("track_id", flat=True)
        )

        added = 0
        with transaction.atomic():
            # Determine starting position
            max_pos = PlaylistItem.objects.filter(playlist=playlist).aggregate(
                m=Max("position")
            )["m"]
            pos = (max_pos if max_pos is not None else -1) + 1

            to_create = []
            for tid in track_ids:
                if tid in existing:
                    continue
                to_create.append(
                    PlaylistItem(playlist=playlist, track_id=tid, position=pos)
                )
                pos += 1
                added += 1

            if to_create:
                PlaylistItem.objects.bulk_create(to_create, ignore_conflicts=True)

        skipped = len(track_ids) - added
        return JsonResponse({"ok": True, "added": added, "skipped": skipped})

    # Guest
    added, skipped = _session_bulk_add(request, track_ids)
    return JsonResponse({"ok": True, "added": added, "skipped": skipped})


@require_POST
def reorder(request):
    """
    Persist order:
      - Auth: expects JSON { "order": [playlist_item_id, ...] }
      - Guest: expects JSON { "order": [track_id, ...] }
    """
    try:
        payload = json.loads(request.body or "{}")
        order = [int(x) for x in payload.get("order", [])]
    except Exception:
        return JsonResponse({"ok": False, "error": "Bad JSON"}, status=400)

    if not order:
        return JsonResponse({"ok": True})

    if request.user.is_authenticated:
        playlist = _get_default_playlist(request.user)
        items = PlaylistItem.objects.filter(playlist=playlist, id__in=order)
        by_id = {it.id: it for it in items}

        pos = 1
        to_update = []
        for iid in order:
            it = by_id.get(iid)
            if it:
                it.position = pos
                to_update.append(it)
                pos += 1

        with transaction.atomic():
            if to_update:
                PlaylistItem.objects.bulk_update(to_update, ["position"])

        return JsonResponse({"ok": True})

    # Guest: reorder by track IDs
    _session_reorder(request, order)
    return JsonResponse({"ok": True})


# ---------- Compatibility shims for old imports ----------


def _guest_get(request):
    """Return guest playlist as a list of track IDs (session-based)."""
    return _session_get_list(request)


def _guest_set(request, ids):
    """Replace guest playlist with given list of track IDs."""
    _session_set_list(request, ids)


def _guest_toggle(request, track_id: int):
    """Toggle a track for guest; returns True if now in playlist."""
    return _session_toggle_track(request, int(track_id))


def _guest_bulk_add(request, ids):
    """Add multiple tracks for guest; returns (added, skipped)."""
    # normalize to ints
    norm = []
    for x in ids:
        try:
            norm.append(int(x))
        except Exception:
            continue
    return _session_bulk_add(request, norm)


def _guest_reorder(request, order_ids):
    """Reorder guest playlist by track IDs."""
    # normalize to ints
    norm = []
    for x in order_ids:
        try:
            norm.append(int(x))
        except Exception:
            continue
    _session_reorder(request, norm)


def _guest_clear(request):
    """Clear guest playlist."""
    _session_set_list(request, [])
