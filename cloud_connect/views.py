# cloud_connect/views.py
import json
import re

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse, StreamingHttpResponse)
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from album.models import Album, AlbumTrack
from tracks.models import Track

from .models import CloudAccount, CloudFileMap, CloudFolderLink
from .providers.gdrive import GoogleDriveProvider

# ---------- OAuth: connect & callback ----------


@login_required
def connect(request, provider: str):
    if provider != "gdrive":
        return HttpResponseBadRequest("Unsupported provider")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=settings.GOOGLE_OAUTH_SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["cloud_oauth_state"] = state
    return redirect(auth_url)


@login_required
def callback(request, provider: str):
    if provider != "gdrive":
        return HttpResponseBadRequest("Unsupported provider")

    state = request.session.get("cloud_oauth_state")
    if not state:
        return HttpResponseBadRequest("Missing state")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials
    CloudAccount.objects.create(
        user=request.user,
        provider="gdrive",
        label="Google Drive",
        token_json=creds.to_json(),
    )
    return redirect("profile:profile")  # go back to profile


# ---------- Link album to a cloud folder ----------


@require_POST
@login_required
def link_album_folder(request, album_id: int):
    """Link an album to a cloud folder. Always respond with JSON."""

    def jerr(msg, code=400):
        return JsonResponse({"ok": False, "error": msg}, status=code)

    # Album belongs to current user?
    album = Album.objects.filter(pk=album_id, owner=request.user).first()
    if not album:
        return jerr("Album not found or not yours.", 404)

    # Accept both FormData and JSON bodies
    account_id = request.POST.get("account_id")
    folder = request.POST.get("folder_url") or request.POST.get("folder_id")

    if not (account_id and folder):
        # try JSON body
        try:
            payload = json.loads(request.body.decode() or "{}")
        except Exception:
            payload = {}
        account_id = account_id or payload.get("account_id")
        folder = folder or payload.get("folder_url") or payload.get("folder_id")

    if not account_id:
        return jerr("Missing account_id.", 400)
    if not folder:
        return jerr("Missing folder_url.", 400)

    account = CloudAccount.objects.filter(pk=account_id, user=request.user).first()
    if not account:
        return jerr("Cloud account not found.", 404)

    # If it’s a Google Drive folder URL, extract the folder ID
    if account.provider == "gdrive":
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder)
        if m:
            folder = m.group(1)

    CloudFolderLink.objects.update_or_create(
        album=album, defaults={"account": account, "folder_id": folder}
    )
    return JsonResponse(
        {"ok": True, "album": album.id, "account": account.id, "folder_id": folder}
    )


# ---------- Sync files into the album ----------


@login_required
def sync_album(request, album_id: int):
    album = get_object_or_404(Album, pk=album_id, owner=request.user)
    link = getattr(album, "cloud_link", None)
    if not link:
        return JsonResponse({"ok": False, "error": "Album not linked"}, status=400)

    acc = link.account
    if acc.provider != "gdrive":
        return JsonResponse(
            {"ok": False, "error": "Provider not implemented"}, status=400
        )

    # Ensure valid token (refresh if needed)
    info = json.loads(acc.token_json)
    creds = Credentials.from_authorized_user_info(info, settings.GOOGLE_OAUTH_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        acc.token_json = creds.to_json()
        acc.save(update_fields=["token_json"])

    provider = GoogleDriveProvider(acc.token_json, settings.GOOGLE_OAUTH_SCOPES)
    files = list(provider.list_audio_files(link.folder_id))

    existing = {
        m.file_id: m
        for m in CloudFileMap.objects.filter(link=link).select_related("track")
    }
    imported = updated = 0

    for f in files:
        fid, name, mime, size, etag = (
            f["id"],
            f["name"],
            f["mime"],
            f["size"],
            f.get("etag") or "",
        )
        if fid in existing:
            m = existing[fid]
            changed = False
            if m.name != name:
                m.name, changed = name, True
            if m.mime != mime:
                m.mime, changed = mime, True
            if m.size != size:
                m.size, changed = size, True
            if m.etag != etag:
                m.etag, changed = etag, True
            if changed:
                m.save()
                updated += 1
            track = m.track
        else:
            track = Track.objects.create(
                owner=request.user, name=name, source_url=provider.stream_url(fid)
            )
            CloudFileMap.objects.create(
                link=link,
                file_id=fid,
                track=track,
                name=name,
                mime=mime,
                size=size,
                etag=etag,
            )
            imported += 1

        AlbumTrack.objects.get_or_create(album=album, track=track)

    link.last_sync = timezone.now()
    link.save(update_fields=["last_sync"])
    return JsonResponse(
        {"ok": True, "imported": imported, "updated": updated, "total": len(files)}
    )


# ---------- Stream proxy (supports Range for scrubbing) ----------

# @login_required
# def stream_file(request, provider: str, file_id: str):
#     """
#     Proxy a Google Drive file to the client, using the *owner's* OAuth token
#     (found via CloudFileMap) so other users can play shared/public tracks.
#     """
#     if provider != "gdrive":
#         return HttpResponseBadRequest("Unsupported provider")

#     # Look up which cloud account owns this file
#     mapping = (
#         CloudFileMap.objects
#         .select_related("link__account")
#         .filter(file_id=file_id)
#         .first()
#     )
#     if not mapping:
#         return HttpResponseBadRequest("File not found")

#     acc = mapping.link.account

#     # Normalize scopes (can be list/tuple or a JSON/string)
#     raw_scopes = getattr(settings, "GOOGLE_OAUTH_SCOPES", [])
#     if isinstance(raw_scopes, (list, tuple, set)):
#         scopes = list(raw_scopes)
#     elif isinstance(raw_scopes, str):
#         raw = raw_scopes.strip()
#         if raw.startswith("["):  # JSON list in env
#             try:
#                 scopes = json.loads(raw)
#             except Exception:
#                 scopes = [raw_scopes]
#         elif " " in raw:
#             scopes = raw.split()
#         else:
#             scopes = [raw_scopes]
#     else:
#         scopes = ["https://www.googleapis.com/auth/drive.readonly"]

#     # Build/refresh credentials from the owner's stored token
#     info = json.loads(acc.token_json)
#     creds = Credentials.from_authorized_user_info(info, scopes=scopes)
#     if (not creds.valid) and creds.refresh_token:
#         creds.refresh(Request())
#         acc.token_json = creds.to_json()
#         acc.save(update_fields=["token_json"])

#     # Prepare Google Drive request (support Range for scrubbing)
#     headers = {"Authorization": f"Bearer {creds.token}"}
#     range_header = request.META.get("HTTP_RANGE")
#     if range_header:
#         headers["Range"] = range_header

#     gurl = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
#     r = requests.get(gurl, headers=headers, stream=True)

#     # If Google returns an error, surface a minimal message
#     if r.status_code in (401, 403, 404):
#         # (Optional: log r.text for debugging)
#         return HttpResponseBadRequest("Unable to fetch file from Drive")

#     # Stream bytes back to the client
#     status = 206 if r.status_code == 206 else 200
#     resp = StreamingHttpResponse(
#         r.iter_content(chunk_size=8192),
#         status=status,
#         content_type=r.headers.get("Content-Type", "audio/mpeg"),
#     )

#     # Pass-through relevant headers
#     if r.headers.get("Content-Length"):
#         resp["Content-Length"] = r.headers["Content-Length"]
#     if r.headers.get("Content-Range"):
#         resp["Content-Range"] = r.headers["Content-Range"]
#         resp.status_code = 206
#     if r.headers.get("Content-Disposition"):
#         resp["Content-Disposition"] = r.headers["Content-Disposition"]

#     resp["Accept-Ranges"] = "bytes"
#     resp["Cache-Control"] = "private, max-age=3600"
#     return resp


@require_GET
def stream_file(request, provider: str, file_id: str):
    """
    Public proxy for Google Drive audio.
    Permits:
      - Owner of the connected Drive account, OR
      - Anyone if the track is in at least one public album.
    Streams bytes with Range support using the owner's token.
    """
    if provider != "gdrive":
        return HttpResponseBadRequest("Unsupported provider")

    # Which file is this, and who owns the token?
    mapping = (
        CloudFileMap.objects.select_related("link__account", "track")
        .filter(file_id=file_id)
        .first()
    )
    if not mapping:
        return HttpResponseBadRequest("File not found")

    owner_user_id = mapping.link.account.user_id

    # Permission: owner OR public album contains this track
    is_owner = request.user.is_authenticated and request.user.id == owner_user_id
    is_public = AlbumTrack.objects.filter(
        track=mapping.track, album__is_public=True
    ).exists()

    if not (is_owner or is_public):
        return HttpResponseForbidden("Track is not public.")

    # Normalize scopes from settings (handles list/space-separated/JSON string)
    raw_scopes = getattr(settings, "GOOGLE_OAUTH_SCOPES", [])
    if isinstance(raw_scopes, (list, tuple, set)):
        scopes = list(raw_scopes)
    elif isinstance(raw_scopes, str):
        s = raw_scopes.strip()
        if s.startswith("["):
            try:
                scopes = json.loads(s)
            except Exception:
                scopes = [raw_scopes]
        elif " " in s:
            scopes = s.split()
        else:
            scopes = [raw_scopes]
    else:
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    # Build/refresh owner credentials
    info = json.loads(mapping.link.account.token_json)
    creds = Credentials.from_authorized_user_info(info, scopes=scopes)
    if (not creds.valid) and creds.refresh_token:
        creds.refresh(Request())
        mapping.link.account.token_json = creds.to_json()
        mapping.link.account.save(update_fields=["token_json"])

    # Proxy request to Drive (support Range for scrubbing)
    headers = {"Authorization": f"Bearer {creds.token}"}
    if request.META.get("HTTP_RANGE"):
        headers["Range"] = request.META["HTTP_RANGE"]

    g_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    r = requests.get(g_url, headers=headers, stream=True)

    if r.status_code in (401, 403, 404):
        # Optional: log r.text for diagnostics
        return HttpResponseBadRequest("Unable to fetch file from Drive")

    status = 206 if r.status_code == 206 else 200
    resp = StreamingHttpResponse(
        r.iter_content(chunk_size=8192),
        status=status,
        content_type=r.headers.get("Content-Type", "audio/mpeg"),
    )
    # Pass-through useful headers
    if r.headers.get("Content-Length"):
        resp["Content-Length"] = r.headers["Content-Length"]
    if r.headers.get("Content-Range"):
        resp["Content-Range"] = r.headers["Content-Range"]
        resp.status_code = 206
    if r.headers.get("Content-Disposition"):
        resp["Content-Disposition"] = r.headers["Content-Disposition"]

    resp["Accept-Ranges"] = "bytes"
    resp["Cache-Control"] = "public, max-age=3600"  # safe for public assets
    return resp
