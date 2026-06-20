"""One-time Google OAuth setup — blocked gcloud window mat use karo."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCRIPT_DIR = Path(__file__).resolve().parent
CLIENT_PATH = SCRIPT_DIR / "credentials" / "oauth_client.json"
TOKEN_PATH = SCRIPT_DIR / "credentials" / "google_oauth_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CONSENT_URL = (
    "https://console.cloud.google.com/apis/credentials/consent"
    "?project=coopsindia-daily-14813"
)
CREDENTIALS_URL = (
    "https://console.cloud.google.com/apis/credentials"
    "?project=coopsindia-daily-14813"
)


def ensure_client_file() -> None:
    if CLIENT_PATH.exists():
        return

    print("=" * 60)
    print("STEP 1 — OAuth consent screen (sirf ek baar, 2 minute)")
    print("=" * 60)
    print("1. User type: External")
    print("2. App name: CoopsIndia Daily")
    print("3. Support email: apna Gmail")
    print("4. Publishing status: TESTING (Production nahi)")
    print("5. Test users mein add karo: paldeepak623@gmail.com")
    print("")
    print("STEP 2 — OAuth Client ID banao")
    print("  Create Credentials -> OAuth client ID -> Desktop app")
    print("  Download JSON -> save as:")
    print(f"  {CLIENT_PATH}")
    print("=" * 60)

    webbrowser.open(CONSENT_URL)
    webbrowser.open(CREDENTIALS_URL)
    input("JSON save karne ke baad Enter dabao...")
    if not CLIENT_PATH.exists():
        raise SystemExit(f"File nahi mili: {CLIENT_PATH}")


def run_oauth_flow() -> None:
    ensure_client_file()
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_PATH), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    client = json.loads(CLIENT_PATH.read_text(encoding="utf-8"))
    installed = client.get("installed") or client.get("web") or {}

    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": installed.get("client_id") or creds.client_id,
        "client_secret": installed.get("client_secret") or creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Token saved -> {TOKEN_PATH}")
    print("Ab Google Drive upload kaam karega (GitHub secret ke liye refresh_token copy karo).")


if __name__ == "__main__":
    run_oauth_flow()
