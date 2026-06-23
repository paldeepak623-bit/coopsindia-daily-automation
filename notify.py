"""WhatsApp (CallMeBot), SMS (Twilio), and email alerts after daily job."""
from __future__ import annotations

import base64
import os
import smtplib
import sys
import urllib.parse
import urllib.request
from email.mime.text import MIMEText


def _log(msg: str) -> None:
    print(msg, flush=True)


def _phones() -> list[tuple[str, str]]:
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


def _emails() -> list[str]:
    return [e.strip() for e in os.environ.get("NOTIFY_EMAILS", "").split(",") if e.strip()]


def send_whatsapp(phone: str, apikey: str, text: str) -> None:
    url = (
        "https://api.callmebot.com/whatsapp.php?"
        + urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey})
    )
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
        body = r.read().decode(errors="replace")
    _log(f"WhatsApp {phone}: {body[:160]}")


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


def send_email(subject: str, body: str, recipients: list[str]) -> None:
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if not user or not password:
        _log("Email skipped — set SMTP_USER and SMTP_PASSWORD in GitHub secrets")
        return
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ.get("SMTP_FROM", user).strip()
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(sender, recipients, msg.as_string())
    _log(f"Email sent to: {', '.join(recipients)}")


def main() -> int:
    status = (sys.argv[1] if len(sys.argv) > 1 else "success").lower()
    folder = os.environ.get("REPORT_FOLDER", "")
    when = os.environ.get("JOB_TIME_IST", "")
    if status == "success":
        text = f"CoopsIndia 7AM OK — DCT report uploaded. Drive folder: {folder}. {when}"
        subject = f"CoopsIndia 7AM OK — {folder}"
    else:
        text = f"CoopsIndia 7AM FAILED — check GitHub Actions. {when}"
        subject = "CoopsIndia 7AM FAILED"

    sent = 0
    for phone, wa_key in _phones():
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

    emails = _emails()
    if emails:
        try:
            send_email(subject, text, emails)
            sent += 1
        except Exception as e:
            _log(f"Email error: {e}")

    if not sent and not emails:
        _log("No notification targets configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
