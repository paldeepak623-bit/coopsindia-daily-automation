"""Fix OneDrive for SharePoint personal folder."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONF = SCRIPT_DIR / "rclone.conf"
RCLONE = SCRIPT_DIR / "tools" / "rclone-v1.74.3-windows-amd64" / "rclone.exe"
SITE_URL = "https://cripson-my.sharepoint.com/personal/abhinandan_kumar_nectarinfotel_in"


def load_onedrive_token_line() -> str:
    text = CONF.read_text(encoding="utf-8")
    m = re.search(r"(\[onedrive\][\s\S]*)", text)
    if not m:
        raise SystemExit("onedrive section missing")
    block = m.group(1)
    tm = re.search(r"token = (\{.*\})", block, re.DOTALL)
    if not tm:
        raise SystemExit("token missing")
    return tm.group(1)


def main() -> None:
    token_line = load_onedrive_token_line()
    new_block = (
        "[onedrive]\n"
        "type = onedrive\n"
        "drive_type = documentLibrary\n"
        f"site_url = {SITE_URL}\n"
        f"token = {token_line}\n"
    )
    text = CONF.read_text(encoding="utf-8")
    text = re.sub(r"\[onedrive\][\s\S]*", new_block, text, count=1)
    CONF.write_text(text, encoding="utf-8")
    print("OneDrive config updated for SharePoint site")

    proc = subprocess.run(
        [str(RCLONE), "lsd", "onedrive:", "--config", str(CONF)],
        capture_output=True,
        text=True,
    )
    print(proc.stdout or proc.stderr)


if __name__ == "__main__":
    main()
