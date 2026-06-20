"""Google Drive + OneDrive upload for daily CoopsIndia report."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

from google_drive_upload import upload_to_google_drive

SCRIPT_DIR = Path(__file__).resolve().parent
RCLONE_CONF = SCRIPT_DIR / "rclone.conf"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _rclone_exe() -> Path | None:
    bundled = SCRIPT_DIR / "tools" / "rclone-v1.74.3-windows-amd64" / "rclone.exe"
    if bundled.exists():
        return bundled
    return None


def upload_to_onedrive_local(
    file_path: Path,
    *,
    sync_root: Path,
    dated_subfolder: str,
) -> Path:
    dest_dir = sync_root / dated_subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file_path.name
    shutil.copy2(file_path, dest)
    _log(f"OneDrive sync OK -> {dest}")
    return dest


def upload_to_onedrive_rclone(
    file_path: Path,
    *,
    remote: str,
    dated_subfolder: str,
    config_path: Path | None = None,
) -> str:
    conf = config_path or RCLONE_CONF
    if not conf.exists() and os.environ.get("RCLONE_CONFIG_B64"):
        conf = SCRIPT_DIR / ".rclone_runtime.conf"
        conf.write_bytes(base64.b64decode(os.environ["RCLONE_CONFIG_B64"]))

    rclone = os.environ.get("RCLONE_BIN", "rclone")
    if os.name == "nt":
        local = _rclone_exe()
        if local:
            rclone = str(local)

    dest = f"{remote}:{dated_subfolder}/{file_path.name}"
    cmd = [rclone, "copyto", str(file_path), dest, "--config", str(conf), "-v"]
    _log(f"OneDrive rclone -> {dest}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return dest


def upload_report(
    file_path: Path,
    dated_subfolder: str,
    upload_cfg: dict,
) -> dict[str, str]:
    results: dict[str, str] = {}

    gcfg = upload_cfg.get("google_drive") or {}
    if gcfg.get("enabled"):
        folder_id = gcfg.get("folder_id", "")
        if not folder_id:
            raise ValueError("google_drive.folder_id config mein set karein")
        results["google_drive"] = upload_to_google_drive(
            file_path,
            root_folder_id=folder_id,
            dated_subfolder=dated_subfolder,
        )

    ocfg = upload_cfg.get("onedrive") or {}
    if ocfg.get("enabled"):
        if ocfg.get("rclone_remote"):
            results["onedrive"] = upload_to_onedrive_rclone(
                file_path,
                remote=ocfg["rclone_remote"],
                dated_subfolder=dated_subfolder,
            )
        elif ocfg.get("local_sync_path"):
            sync_root = Path(ocfg["local_sync_path"])
            results["onedrive"] = str(
                upload_to_onedrive_local(
                    file_path,
                    sync_root=sync_root,
                    dated_subfolder=dated_subfolder,
                )
            )
        else:
            raise ValueError("onedrive: local_sync_path ya rclone_remote set karein")

    return results


def load_upload_config(config_path: Path | None = None) -> dict:
    path = config_path or SCRIPT_DIR / "config.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("upload") or {}
