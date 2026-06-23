"""Send WhatsApp (CallMeBot) and/or SMS (Twilio) after daily job."""
from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request


def _log(msg: str) -> None:
    print(msg, flush=True)


def send_whatsapp(phone: str, apikey: str, text: str) -> bool:
  url = (
      "https://api.callmebot.com/whatsapp.php?"
      + urllib.parse.urlencode({"phone": phone, "text": text, "apikey": apikey})
  )
  req = urllib.request.Request(url)
  with urllib.request.urlopen(req, timeout=30) as r:
    body = r.read().decode(errors="replace")
  _log(f"WhatsApp: {body[:200]}")
  return True


def send_sms_twilio(to: str, body: str) -> bool:
  sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
  token = os.environ.get("TWILIO_AUTH_TOKEN", "")
  from_no = os.environ.get("TWILIO_FROM_NUMBER", "")
  if not all([sid, token, from_no, to]):
    return False
  data = urllib.parse.urlencode({"To": to, "From": from_no, "Body": body}).encode()
  url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
  req = urllib.request.Request(url, data=data, method="POST")
  import base64

  auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
  req.add_header("Authorization", f"Basic {auth}")
  req.add_header("Content-Type", "application/x-www-form-urlencoded")
  with urllib.request.urlopen(req, timeout=30) as r:
    _log(f"SMS: {r.status}")
  return True


def main() -> int:
  status = (sys.argv[1] if len(sys.argv) > 1 else "success").lower()
  folder = os.environ.get("REPORT_FOLDER", "")
  when = os.environ.get("JOB_TIME_IST", "")
  if status == "success":
    text = f"CoopsIndia 7AM OK — DCT report uploaded to Drive folder {folder}. {when}"
  else:
    text = f"CoopsIndia 7AM FAILED — check GitHub Actions. {when}"

  phone = os.environ.get("NOTIFY_PHONE", "").strip()
  wa_key = os.environ.get("CALLMEBOT_APIKEY", "").strip()
  sent = False
  if phone and wa_key:
    try:
      send_whatsapp(phone, wa_key, text)
      sent = True
    except Exception as e:
      _log(f"WhatsApp error: {e}")
  if phone:
    try:
      if send_sms_twilio(phone, text):
        sent = True
    except Exception as e:
      _log(f"SMS error: {e}")
  if not sent:
    _log("No notification sent (set NOTIFY_PHONE + CALLMEBOT_APIKEY or Twilio secrets)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
