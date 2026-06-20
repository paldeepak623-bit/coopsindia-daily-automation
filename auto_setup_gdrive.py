"""Auto-build Google Drive rclone config from gcloud login (no browser)."""
from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCRIPT_DIR = Path(__file__).resolve().parent
ADC = Path.home() / "AppData/Roaming/gcloud/application_default_credentials.json"
CONF = SCRIPT_DIR / "rclone.conf"
GDRIVE_FOLDER = "1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5"
SCOPE = ["https://www.googleapis.com/auth/cloud-platform"]


def main() -> None:
    if not ADC.exists():
        raise SystemExit(f"ADC missing: {ADC}")

    adc = json.loads(ADC.read_text(encoding="utf-8"))
    creds = Credentials(
        token=None,
        refresh_token=adc["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=adc["client_id"],
        client_secret=adc["client_secret"],
        scopes=SCOPE,
    )
    creds.refresh(Request())

    token = {
        "access_token": creds.token,
        "token_type": "Bearer",
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.strftime("%Y-%m-%dT%H:%M:%SZ") if creds.expiry else "",
    }
    token_str = json.dumps(token)

    lines = [
        "[gdrive]",
        "type = drive",
        "scope = drive",
        f"token = {token_str}",
        f"root_folder_id = {GDRIVE_FOLDER}",
        "",
    ]

    if CONF.exists():
        existing = CONF.read_text(encoding="utf-8")
        if "[onedrive]" in existing:
            od_section = existing[existing.index("[onedrive]") :]
            lines.append(od_section.strip())
            if not lines[-1].endswith("\n"):
                lines.append("")

    CONF.write_text("\n".join(lines), encoding="utf-8")

    oauth_path = SCRIPT_DIR / "credentials" / "google_oauth_token.json"
    oauth_path.parent.mkdir(parents=True, exist_ok=True)
    oauth_path.write_text(
        json.dumps(
            {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": adc["client_id"],
                "client_secret": adc["client_secret"],
                "scopes": SCOPE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Google Drive rclone OK -> {CONF}")


if __name__ == "__main__":
    main()
