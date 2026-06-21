# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python automation tool (no web server, no database, no
exposed ports). It uses Playwright (headless Chromium) to log into the CoopsIndia
UP portal, downloads the "DCT Status Summary" report, converts CSV → `.xlsx`
(`openpyxl`), and uploads it to Google Drive via `rclone`. Entry point:
`daily_job.py` (see `SETUP_AUTOMATION.md` for full product/setup docs).

### Environment
- Python deps live in a virtualenv at `.venv` (gitignored). Run tools via
  `.venv/bin/python` / `.venv/bin/playwright`. The update script (re)creates
  `.venv` and installs `requirements.txt` + Playwright Chromium.
- One-off system deps already baked into the VM snapshot (NOT in the update
  script): `python3.12-venv`, Playwright's Chromium OS libraries
  (`sudo .venv/bin/playwright install-deps chromium`), and the `rclone` binary
  (`curl https://rclone.org/install.sh | sudo bash`). Reinstall these manually
  only if a fresh VM is missing them.

### Lint / test / build / run
- No lint config, no test suite, and no build step exist in this repo. The
  available "lint" is a compile check: `.venv/bin/python -m py_compile *.py`.
- Run the app: `.venv/bin/python daily_job.py --headless`. On Linux it defaults
  to headless; `--visible` needs a display and is intended for Windows.

### Important caveats
- Running `daily_job.py` end-to-end hits the LIVE government portal
  (`up.coopsindia.com`) with real credentials and the portal allows only ONE
  active session (it force-logs-out / waits ~3 min if a session is busy). Do not
  run the full job casually; prefer exercising core logic in isolation.
- `daily_job.py` requires a `config.json` (copy `config.example.json`) with
  `login_id`/`password`; without it the job exits 1 with a clear message and
  writes to `logs/daily_YYYYMMDD.log`.
- The default upload path needs `rclone.conf` defining a `gdrive` remote (or
  `RCLONE_CONFIG_B64` env var). Without it, upload raises `FileNotFoundError`.
- Note: `coops_login.py` contains hardcoded production credentials and a Google
  Drive folder ID — treat as sensitive.
