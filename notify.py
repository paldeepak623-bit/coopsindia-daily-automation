"""Send WhatsApp (CallMeBot) and/or SMS (Twilio) to one or more numbers."""
from __future__ import annotations

import base64
import os
import sys
import urllib.parse
import urllib.request


def _log(msg: str) -> None:
    print(msg, flush=True)


def _pairs() -> list[tuple[str, str]]:
    """Phone + CallMeBot API key pairs from NOTIFY_TARGETS or NOTIFY_PHONES + CALLMEBOT_APIKEYS."""
    targets = os.environ.get("NOTIFY_TARGETS", "").strip()
    if targets:
        out: list[tuple[str, str]] = []
        for part in targets.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                phone, key = part.split(":", 1)
                out.append((phone.strip(), key.strip()))
            else:
                out.append((part, ""))
        return out
    phones = [p.strip() for p in os.environ.get("NOTIFY_PHONES", "").split(",") if p.strip()]
    keys = [k.strip() for k in os.environ.get("CALLMEBOT_APIKEYS", "").split(",") if k.strip()]
    default_key = os.environ.get("CALLMEBOT_APIKEY", "").strip()
    out = []
    for i, phone in enumerate(phones):
        key = keys[i] if i < len(keys) else (keys[0] if len(keys) == 1 else default_key)
        out.append((phone, key))
    return out


def send_whatsapp(phone: str, apikey: str, text: str) -> bool:
    url = (
        "https://api.callmebot.com/whatsapp.php?"
        + urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey})
    )
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
        body = r.read().decode(errors="replace")
    _log(f"WhatsApp {phone}: {body[:160]}")
    return True


def send_sms_twilio(to: str, body: str) -> bool:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_no = os.environ.get("TWILIO_FROM_NUMBER", "")
    if not all([sid, token, from_no]):
        return False
    data = urllib.parse.urlencode({"To": to, "From": from_no, "Body": body}).encode()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        _log(f"SMS {to}: HTTP {r.status}")
    return True


def main() -> int:
    status = (sys.argv[1] if len(sys.argv) > 1 else "success").lower()
    folder = os.environ.get("REPORT_FOLDER", "")
    when = os.environ.get("JOB_TIME_IST", "")
    if status == "success":
        text = f"CoopsIndia 7AM OK — DCT report uploaded. Drive folder: {folder}. {when}"
    else:
        text = f"CoopsIndia 7AM FAILED — check GitHub Actions. {when}"

    pairs = _pairs()
    if not pairs:
        _log("No NOTIFY_PHONES configured")
        return 0

    sent = 0
    for phone, wa_key in pairs:
        if wa_key:
            try:
                send_whatsapp(phone, wa_key, text)
                sent += 1
            except Exception as e:
                _log(f"WhatsApp error {phone}: {e}")
        try:
            if send_sms_twilio(phone, text):
                sent += 1
        except Exception as e:
            _log(f"SMS error {phone}: {e}")

    if not sent:
        _log("No message sent — add CallMeBot API keys (one per phone) in GitHub secrets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
