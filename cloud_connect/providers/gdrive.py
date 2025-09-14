# cloud_connect/providers/gdrive.py
import json
from typing import Iterable
from django.urls import reverse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class GoogleDriveProvider:
    def __init__(self, token_json: str, scopes: list[str]):
        self._raw = token_json
        creds = Credentials.from_authorized_user_info(json.loads(token_json), scopes)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # caller should persist creds.to_json() if changed
        self.creds = creds
        self.service = build("drive", "v3", credentials=self.creds, cache_discovery=False)

    def list_audio_files(self, folder_id: str) -> Iterable[dict]:
        q = f"'{folder_id}' in parents and mimeType contains 'audio/' and trashed = false"
        fields = "nextPageToken, files(id,name,mimeType,md5Checksum,size)"
        page = None
        while True:
            resp = self.service.files().list(q=q, fields=fields, pageSize=1000, pageToken=page).execute()
            for f in resp.get("files", []):
                yield {
                    "id": f["id"],
                    "name": f["name"],
                    "mime": f.get("mimeType") or "",
                    "size": int(f["size"]) if f.get("size") else None,
                    "etag": f.get("md5Checksum") or "",
                }
            page = resp.get("nextPageToken")
            if not page: break

    def stream_url(self, file_id: str) -> str:
        return reverse("cloud:stream", args=("gdrive", file_id))
