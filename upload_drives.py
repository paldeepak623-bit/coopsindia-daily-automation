"""Google Drive upload — rclone (cloud) + optional local sync."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RCLONE_CONF = SCRIPT_DIR / "rclone.conf"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _rclone_config_path() -> Path:
    if RCLONE_CONF.exists():
        return RCLONE_CONF
    b64 = os.environ.get("RCLONE_CONFIG_B64", "")
    if b64:
        runtime = SCRIPT_DIR / ".rclone_runtime.conf"
        runtime.write_bytes(base64.b64decode(b64))
        return runtime
    return RCLONE_CONF


def _rclone_exe() -> str:
    env_bin = os.environ.get("RCLONE_BIN")
    if env_bin:
        return env_bin
    bundled = SCRIPT_DIR / "tools" / "rclone-v1.74.3-windows-amd64" / "rclone.exe"
    if bundled.exists():
        return str(bundled)
    return "rclone"


def upload_via_rclone(
    file_path: Path,
    *,
    remote: str,
    dated_subfolder: str,
) -> str:
    conf = _rclone_config_path()
    if not conf.exists():
        raise FileNotFoundError(
            "rclone.conf missing — ek baar chalao: .\\setup_rclone_all.ps1"
        )

    dest = f"{remote}:{dated_subfolder}/{file_path.name}"
    mkdir_cmd = [
        _rclone_exe(),
        "mkdir",
        f"{remote}:{dated_subfolder}",
        "--config",
        str(conf),
    ]
    subprocess.run(mkdir_cmd, capture_output=True, text=True)
    cmd = [
        _rclone_exe(),
        "copyto",
        str(file_path),
        dest,
        "--config",
        str(conf),
    ]
    _log(f"rclone upload -> {dest}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "rclone upload failed")
    return dest


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


def upload_report(
    file_path: Path,
    dated_subfolder: str,
    upload_cfg: dict,
) -> dict[str, str]:
    results: dict[str, str] = {}

    gcfg = upload_cfg.get("google_drive") or {}
    if gcfg.get("enabled"):
        remote = gcfg.get("rclone_remote", "gdrive")
        results["google_drive"] = upload_via_rclone(
            file_path, remote=remote, dated_subfolder=dated_subfolder
        )

    ocfg = upload_cfg.get("onedrive") or {}
    if ocfg.get("enabled"):
        if ocfg.get("use_graph", True):
            from onedrive_graph_upload import upload_to_onedrive_graph

            results["onedrive"] = upload_to_onedrive_graph(file_path, dated_subfolder)
        elif ocfg.get("rclone_remote"):
            results["onedrive"] = upload_via_rclone(
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
            raise ValueError("onedrive: rclone_remote ya local_sync_path set karein")

    return results


def load_upload_config(config_path: Path | None = None) -> dict:
    path = config_path or SCRIPT_DIR / "config.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("upload") or {}
