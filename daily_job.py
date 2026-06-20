"""
Daily CoopsIndia job — subah 9 baje (Task Scheduler / GitHub Actions se chale).

1. Kal ki date ka folder (DD-MM-YYYY) Google Drive par
2. Login -> Excel download (temp) -> Logout
3. Sirf Google Drive par upload — local downloads folder mein save NAHI
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from coops_login import (
    DOWNLOAD_DIR,
    FlowError,
    LoginError,
    job_download_dir,
    load_config,
    log,
    report_folder_name,
    run_flow,
)
from upload_drives import load_upload_config, upload_report

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
GDRIVE_FOLDER_ID = "1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5"


def write_log_line(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"daily_{datetime.now():%Y%m%d}.log"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(line)
    log(msg)


def credentials_from_config(cfg: dict) -> tuple[str, str]:
    login_id = cfg.get("login_id") or cfg.get("coops", {}).get("login_id", "")
    password = cfg.get("password") or cfg.get("coops", {}).get("password", "")
    if not login_id or not password:
        raise ValueError("config.json mein login_id aur password set karein")
    return login_id, password


def resolve_download_dir(cfg: dict, folder_name: str) -> tuple[Path, bool]:
    """Return (download_dir, should_cleanup_after_upload)."""
    report_cfg = cfg.get("report") or {}
    keep_local = report_cfg.get("keep_local_copy", False)

    if keep_local:
        base = Path(report_cfg.get("local_root") or DOWNLOAD_DIR)
        if not base.is_absolute():
            base = SCRIPT_DIR / base
        return job_download_dir(base, use_yesterday=report_cfg.get("use_yesterday_date", True)), False

    temp_root = Path(tempfile.mkdtemp(prefix="coops_dl_"))
    target = temp_root / folder_name
    target.mkdir(parents=True, exist_ok=True)
    return target, True


def run_daily_job(*, headless: bool = True) -> Path:
    cfg = load_config()
    login_id, password = credentials_from_config(cfg)

    report_cfg = cfg.get("report") or {}
    use_yesterday = report_cfg.get("use_yesterday_date", True)
    folder_name = report_folder_name(use_yesterday=use_yesterday)
    target_dir, cleanup_temp = resolve_download_dir(cfg, folder_name)

    write_log_line(
        f"Job start — Google Drive folder: {folder_name} "
        f"(parent: https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID})"
    )
    if cleanup_temp:
        write_log_line(f"Temp download only (local save nahi): {target_dir}")

    report_path = run_flow(
        login_id,
        password,
        keep_open=False,
        skip_download=False,
        download_dir=target_dir,
        headless=headless,
    )
    if not report_path or not report_path.exists():
        raise FlowError("Excel file download nahi hui")

    write_log_line(f"Download OK: {report_path.name}")

    upload_cfg = load_upload_config()
    if not upload_cfg:
        raise ValueError("config.json upload section empty — Google Drive enable karein")

    gcfg = upload_cfg.get("google_drive") or {}
    if not gcfg.get("enabled"):
        raise ValueError("Google Drive upload disabled — config.json mein enabled: true karein")

    try:
        results = upload_report(report_path, folder_name, upload_cfg)
        for name, dest in results.items():
            write_log_line(f"Upload {name}: {dest}")
    except FileNotFoundError as exc:
        write_log_line(f"Upload FAILED — setup pending: {exc}")
        raise
    except Exception as exc:
        write_log_line(f"Upload FAILED: {exc}")
        raise
    finally:
        if cleanup_temp:
            shutil.rmtree(target_dir.parent, ignore_errors=True)
            write_log_line("Temp download folder delete ho gaya — sirf Google Drive par file hai")

    write_log_line("Job complete")
    return report_path


def main() -> int:
    os.environ["COOPS_AUTO"] = "1"
    if "--headless" in sys.argv:
        headless = True
    elif "--visible" in sys.argv:
        headless = False
    else:
        headless = sys.platform != "win32"
    try:
        run_daily_job(headless=headless)
        return 0
    except (LoginError, FlowError, ValueError, FileNotFoundError) as exc:
        write_log_line(f"FAILED: {exc}")
        return 1
    except Exception as exc:
        write_log_line(f"FAILED: {exc}")
        write_log_line(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
