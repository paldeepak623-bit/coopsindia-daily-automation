"""
Daily CoopsIndia job — subah 9 baje (Task Scheduler / GitHub Actions se chale).

1. Kal ki date ka folder (DD-MM-YYYY)
2. Login -> Excel download -> Logout
3. Google Drive + OneDrive par upload
"""

from __future__ import annotations

import json
import sys
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


def run_daily_job(*, headless: bool = True) -> Path:
    cfg = load_config()
    login_id, password = credentials_from_config(cfg)

    report_cfg = cfg.get("report") or {}
    use_yesterday = report_cfg.get("use_yesterday_date", True)
    base = Path(report_cfg.get("local_root") or DOWNLOAD_DIR)
    if not base.is_absolute():
        base = SCRIPT_DIR / base

    folder_name = report_folder_name(use_yesterday=use_yesterday)
    target_dir = job_download_dir(base, use_yesterday=use_yesterday)
    write_log_line(f"Job start — folder: {folder_name} -> {target_dir}")

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

    write_log_line(f"Download OK: {report_path}")

    upload_cfg = load_upload_config()
    if upload_cfg:
        results = upload_report(report_path, folder_name, upload_cfg)
        for name, dest in results.items():
            write_log_line(f"Upload {name}: {dest}")
    else:
        write_log_line("Upload skip — config.json upload section empty")

    write_log_line("Job complete")
    return report_path


def main() -> int:
    headless = "--visible" not in sys.argv
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
