"""Google Drive upload — OAuth refresh token (service account files upload nahi kar sakta)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_PATH = SCRIPT_DIR / "credentials" / "google_oauth_token.json"
CLIENT_PATH = SCRIPT_DIR / "credentials" / "oauth_client.json"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _load_client_info() -> tuple[str, str]:
    env_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    env_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    if env_id and env_secret:
        return env_id, env_secret

    if CLIENT_PATH.exists():
        data = json.loads(CLIENT_PATH.read_text(encoding="utf-8"))
        installed = data.get("installed") or data.get("web") or {}
        cid = installed.get("client_id", "")
        secret = installed.get("client_secret", "")
        if cid and secret:
            return cid, secret

    raise FileNotFoundError(
        "OAuth client missing. Run: python setup_google_oauth.py "
        "(credentials/oauth_client.json chahiye)"
    )


def _load_token_data() -> dict:
    env_refresh = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
    if env_refresh:
        client_id, client_secret = _load_client_info()
        return {
            "refresh_token": env_refresh,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_uri": TOKEN_URI,
            "scopes": [DRIVE_SCOPE],
        }

    if TOKEN_PATH.exists():
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        "Google OAuth token missing. Run once: python setup_google_oauth.py"
    )


def get_drive_credentials() -> Credentials:
    data = _load_token_data()
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", TOKEN_URI),
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data.get("scopes") or [DRIVE_SCOPE],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if TOKEN_PATH.exists():
            saved = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            saved["token"] = creds.token
            TOKEN_PATH.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    return creds


def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    q = (
        f"name='{name}' and '{parent_id}' in parents "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    hits = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = hits.get("files") or []
    if files:
        return files[0]["id"]
    created = service.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
    ).execute()
    return created["id"]


def upload_to_google_drive(
    file_path: Path,
    *,
    root_folder_id: str,
    dated_subfolder: str,
) -> str:
    creds = get_drive_credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    subfolder_id = _get_or_create_folder(service, dated_subfolder, root_folder_id)

    media = MediaFileUpload(
        str(file_path),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    uploaded = service.files().create(
        body={"name": file_path.name, "parents": [subfolder_id]},
        media_body=media,
        fields="id,name",
    ).execute()
    link = f"https://drive.google.com/file/d/{uploaded['id']}/view"
    _log(f"Google Drive OK -> {dated_subfolder}/{uploaded['name']}")
    return link
