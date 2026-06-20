"""One-time rclone setup for Google Drive + OneDrive (opens browser twice)."""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS = SCRIPT_DIR / "tools"
RCLONE_ZIP = TOOLS / "rclone.zip"
RCLONE_EXE = TOOLS / "rclone-v1.74.3-windows-amd64" / "rclone.exe"
CONF = SCRIPT_DIR / "rclone.conf"
GDRIVE_FOLDER = "1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5"


def ensure_rclone() -> Path:
    if RCLONE_EXE.exists():
        return RCLONE_EXE
    TOOLS.mkdir(parents=True, exist_ok=True)
    url = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
    print(f"Downloading rclone...")
    urlretrieve(url, RCLONE_ZIP)
    with zipfile.ZipFile(RCLONE_ZIP) as zf:
        zf.extractall(TOOLS)
    return RCLONE_EXE


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out.strip() or "rclone command failed")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def main() -> int:
    rclone = ensure_rclone()
    cfg = ["--config", str(CONF)]

    print("\nSTEP 1/2 - Google Drive (browser)...")
    token = run([str(rclone), "authorize", "drive"])
    run(
        [
            str(rclone),
            "config",
            "create",
            "gdrive",
            "drive",
            "config_token",
            token,
            "root_folder_id",
            GDRIVE_FOLDER,
            *cfg,
        ]
    )

    print("\nSTEP 2/2 - OneDrive (browser)...")
    token = run([str(rclone), "authorize", "onedrive"])
    run(
        [
            str(rclone),
            "config",
            "create",
            "onedrive",
            "onedrive",
            "config_token",
            token,
            "drive_type",
            "business",
            *cfg,
        ]
    )

    print("\nTesting remotes...")
    subprocess.run([str(rclone), "lsd", "gdrive:", *cfg], check=False)
    subprocess.run([str(rclone), "lsd", "onedrive:", *cfg], check=False)
    print(f"\nDONE -> {CONF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
