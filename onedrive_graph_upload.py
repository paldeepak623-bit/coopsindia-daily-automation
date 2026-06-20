"""OneDrive upload via Microsoft Graph."""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONF = SCRIPT_DIR / "rclone.conf"


def _log(msg: str) -> None:
    print(msg, flush=True)


def load_onedrive_token() -> dict:
    text = CONF.read_text(encoding="utf-8")
    m = re.search(r"\[onedrive\][\s\S]*?token = (\{.*\})", text, re.DOTALL)
    if not m:
        raise FileNotFoundError("onedrive token missing in rclone.conf")
    return json.loads(m.group(1))


def _headers(token: dict) -> dict:
    return {"Authorization": f"Bearer {token['access_token']}"}


def get_or_create_folder(token: dict, name: str) -> dict:
    headers = _headers(token)
    children_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    r = requests.get(children_url, headers=headers, timeout=60)
    r.raise_for_status()
    for item in r.json().get("value", []):
        if item.get("name") == name and "folder" in item:
            return item
    r = requests.post(
        children_url,
        headers=headers,
        json={"name": name, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
        timeout=60,
    )
    if r.status_code in (200, 201):
        return r.json()
    r = requests.get(children_url, headers=headers, timeout=60)
    r.raise_for_status()
    for item in r.json().get("value", []):
        if item.get("name") == name:
            return item
    raise RuntimeError(f"Could not create OneDrive folder: {name}")


def upload_to_onedrive_graph(file_path: Path, dated_subfolder: str) -> str:
    token = load_onedrive_token()
    folder = get_or_create_folder(token, dated_subfolder)
    upload_url = (
        f"https://graph.microsoft.com/v1.0/me/drive/items/{folder['id']}:"
        f"/{file_path.name}:/content"
    )
    r = requests.put(
        upload_url,
        headers=_headers(token),
        data=file_path.read_bytes(),
        timeout=120,
    )
    r.raise_for_status()
    web = r.json().get("webUrl", upload_url)
    _log(f"OneDrive OK -> {dated_subfolder}/{file_path.name}")
    return web
