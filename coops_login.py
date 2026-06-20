"""
CoopsIndia UP — Login + DCT Report Excel download + Logout.
Chrome visual mode. Run: run_coops_login.bat
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
from playwright.sync_api import BrowserContext, Page, sync_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "downloads"
CONFIG_PATH = SCRIPT_DIR / "config.json"

URL = "https://up.coopsindia.com/fhruttarpradesh/#/"
DCT_SUMMARY_URL = "https://up.coopsindia.com/fhruttarpradesh/#/dct_summary"
LOGOUT_API = "https://up.coopsindia.com/FhrUttarPradeshService/users/check_user_logout"
LOGIN_ID = "dccbbr.jarb@coopsindia.com"
PASSWORD = "Saharanpur@123"
MAX_WAIT_SEC = 600
RETRY_GAP_SEC = 1.0
SESSION_BUSY_WAIT_SEC = 180  # 2-3 min — server session expire hone do
SESSION_BUSY_MAX_CYCLES = 5

USER_SEL = "#txt_login_user_name"
PASS_SEL = "#txt_login_pws"
CAPTCHA_INPUT_SEL = 'input[name="login_captch_input"]'
CANVAS_SEL = "canvas#textCanvas"
LOGIN_BTN_SEL = 'button:has-text("Login")'
REFRESH_SEL = ".captha-styles-main .fa-refresh"

DOWNLOAD_DROPDOWN_SEL = (
    ".btn-group:has(button:has-text('Download')) button.dropdown-toggle, "
    "button:has-text('Download') + button"
)
CSV_REPORT_SEL = "text=DCT Status Summary CSV Report"

CAPTCHA_HOOK = """
(() => {
  if (window.__captchaHooked) return;
  window.__captchaHooked = true;
  window.__captchaText = '';
  const save = (text) => {
    if (typeof text === 'string' && /^[A-Za-z0-9]{4,8}$/.test(text)) {
      window.__captchaText = text;
    }
  };
  const origGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {
    const ctx = origGetContext.call(this, type, ...args);
    if (type === '2d' && ctx && !ctx.__captchaPatched) {
      ctx.__captchaPatched = true;
      const origFill = ctx.fillText.bind(ctx);
      const origStroke = ctx.strokeText.bind(ctx);
      ctx.fillText = (text, ...rest) => { save(text); return origFill(text, ...rest); };
      ctx.strokeText = (text, ...rest) => { save(text); return origStroke(text, ...rest); };
    }
    return ctx;
  };
})();
"""

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


class LoginError(Exception):
    pass


class FlowError(Exception):
    pass


def log(msg: str) -> None:
    print(msg, flush=True)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def report_folder_name(for_date: datetime | None = None, *, use_yesterday: bool = True) -> str:
    """Job folder: kal ki date DD-MM-YYYY (aaj 20-06-2026 -> 19-06-2026)."""
    dt = for_date or datetime.now()
    if use_yesterday:
        dt = dt - timedelta(days=1)
    return dt.strftime("%d-%m-%Y")


def job_download_dir(base: Path | None = None, *, use_yesterday: bool = True) -> Path:
    root = base or DOWNLOAD_DIR
    folder = report_folder_name(use_yesterday=use_yesterday)
    path = root / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_logged_in(page: Page) -> bool:
    url = page.url.lower()
    return any(x in url for x in ("fhr_dashboard", "fhr_summary", "dct_summary", "workflow"))


def is_login_page(page: Page) -> bool:
    try:
        return page.locator(USER_SEL).is_visible(timeout=1500)
    except Exception:
        return False


def read_captcha_now(page: Page) -> str:
    return page.evaluate("() => window.__captchaText || ''")


def wait_initial_captcha(page: Page, timeout_ms: int = 15000) -> str:
    page.wait_for_selector(CANVAS_SEL, state="visible", timeout=timeout_ms)
    page.wait_for_function(
        "() => (window.__captchaText || '').length >= 4",
        timeout=timeout_ms,
    )
    return read_captcha_now(page)


def refresh_captcha(page: Page, previous: str, timeout_ms: int = 10000) -> str:
    page.locator(REFRESH_SEL).click()
    page.wait_for_function(
        """(prev) => {
            const t = window.__captchaText || '';
            return t.length >= 4 && t !== prev;
        }""",
        arg=previous,
        timeout=timeout_ms,
    )
    return read_captcha_now(page)


def fill_credentials_once(page: Page, login_id: str, password: str) -> None:
    user = page.locator(USER_SEL)
    pwd = page.locator(PASS_SEL)
    if user.input_value().strip().lower() != login_id.strip().lower():
        user.fill(login_id)
    if pwd.input_value() != password:
        pwd.fill(password)


def try_login(page: Page, captcha: str) -> dict | None:
    cap = page.locator(CAPTCHA_INPUT_SEL)
    cap.fill("")
    cap.fill(captcha)
    try:
        with page.expect_response(lambda r: "check_user_login" in r.url, timeout=10000) as resp:
            page.locator(LOGIN_BTN_SEL).click()
        return resp.value.json()
    except Exception:
        return None


def login_ok(result: dict | None, page: Page) -> bool:
    if is_logged_in(page):
        return True
    if not result:
        return False
    return (result.get("status") or "").upper() in ("SUCCESS", "OK", "200")


def do_login(page: Page, login_id: str, password: str) -> int:
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(USER_SEL, state="visible", timeout=30000)
    fill_credentials_once(page, login_id, password)
    log("User ID & password set")

    started = time.time()
    attempt = 0
    captcha = ""
    need_refresh = False
    busy_cycles = 0

    while time.time() - started < MAX_WAIT_SEC:
        if is_logged_in(page):
            log(f"Login OK! -> {page.url}")
            return attempt

        attempt += 1
        if not captcha:
            captcha = wait_initial_captcha(page)
            log(f"Try {attempt}: captcha={captcha} (no refresh)")
        elif need_refresh:
            captcha = refresh_captcha(page, captcha)
            log(f"Try {attempt}: new captcha={captcha}")
        else:
            log(f"Try {attempt}: same captcha={captcha}")

        result = try_login(page, captcha)
        if login_ok(result, page):
            log(f"Login OK! -> {page.url}")
            return attempt

        msg = (result or {}).get("statusMsg") or (result or {}).get("message") or "failed"
        msg_l = msg.lower()
        need_refresh = "captcha" in msg_l

        if need_refresh:
            log(f"Wrong captcha — refresh in {RETRY_GAP_SEC}s")
        elif "already active" in msg_l:
            busy_cycles += 1
            if busy_cycles >= SESSION_BUSY_MAX_CYCLES:
                raise LoginError(
                    "Session ab bhi busy hai — manually logout karein ya aur wait karein."
                )
            wait_min = SESSION_BUSY_WAIT_SEC // 60
            log(
                f"Session busy — turant retry NAHI. "
                f"{wait_min} minute wait ({busy_cycles}/{SESSION_BUSY_MAX_CYCLES})..."
            )
            for remaining in range(SESSION_BUSY_WAIT_SEC, 0, -30):
                log(f"  ... {remaining // 60}m {remaining % 60}s baaki")
                time.sleep(min(30, remaining))
            log("Wait khatam — page reload, naya captcha, dubara login...")
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector(USER_SEL, state="visible", timeout=30000)
            fill_credentials_once(page, login_id, password)
            captcha = ""
            need_refresh = False
            continue
        else:
            need_refresh = True
            log(f"Fail: {msg} — refresh in {RETRY_GAP_SEC}s")
        time.sleep(RETRY_GAP_SEC)

    raise LoginError(f"Login failed after {MAX_WAIT_SEC}s ({attempt} tries)")


def open_dct_status_summary(page: Page) -> None:
    log("Opening Dct Status Summary...")
    page.goto(DCT_SUMMARY_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("text=Dct Summary", timeout=30000)
    time.sleep(1.5)
    log(f"Dct Summary open -> {page.url}")


def cleanup_bad_downloads() -> None:
    """UUID / extension-less junk files hatao."""
    if not DOWNLOAD_DIR.exists():
        return
    for f in DOWNLOAD_DIR.iterdir():
        if not f.is_file():
            continue
        if _UUID_RE.match(f.stem) or f.suffix == "":
            try:
                f.unlink()
                log(f"Removed bad file: {f.name}")
            except Exception:
                pass


def excel_report_name(suggested: str = "") -> str:
    name = (suggested or "").strip()
    if name.lower().endswith(".csv"):
        name = Path(name).stem + ".xlsx"
    elif name.lower().endswith(".xlsx"):
        return name
    elif name and not _UUID_RE.match(Path(name).stem):
        return f"{Path(name).stem}.xlsx"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"DCT_Status_Summary_{ts}.xlsx"


def csv_to_excel(csv_path: Path, xlsx_path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh):
            ws.append(row)
    wb.save(xlsx_path)


def is_valid_csv(path: Path) -> bool:
    if path.stat().st_size < 50:
        return False
    head = path.read_bytes()[:120]
    if not head or head.startswith(b"{"):
        return False
    text = head.decode("utf-8", errors="ignore").upper()
    return "SLNO" in text or "STATE" in text or "," in text


def download_dct_excel_report(page: Page, target_dir: Path | None = None) -> Path:
    log("Downloading DCT Status Summary -> Excel (.xlsx)...")
    out_dir = target_dir or DOWNLOAD_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    cleanup_bad_downloads()

    page.wait_for_selector("text=Grand Total", timeout=45000)
    time.sleep(2)

    last_err = None
    for attempt in range(1, 4):
        csv_tmp = out_dir / f"_tmp_dct_{int(time.time())}.csv"
        try:
            dropdown = page.locator(DOWNLOAD_DROPDOWN_SEL).first
            dropdown.wait_for(state="visible", timeout=20000)
            csv_opt = page.locator(CSV_REPORT_SEL).first

            with page.expect_download(timeout=90000) as dl_info:
                dropdown.click()
                time.sleep(0.6)
                csv_opt.wait_for(state="visible", timeout=10000)
                csv_opt.click()

            download = dl_info.value
            download.save_as(csv_tmp)

            if not is_valid_csv(csv_tmp):
                raise FlowError(f"Invalid CSV content ({csv_tmp.stat().st_size} bytes)")

            xlsx_name = excel_report_name(download.suggested_filename)
            xlsx_path = out_dir / xlsx_name
            if xlsx_path.exists():
                xlsx_path = out_dir / f"{xlsx_path.stem}_{int(time.time())}.xlsx"

            csv_to_excel(csv_tmp, xlsx_path)
            csv_tmp.unlink(missing_ok=True)
            cleanup_bad_downloads()

            if xlsx_path.suffix.lower() != ".xlsx":
                raise FlowError(f"File Excel format mein nahi: {xlsx_path.name}")
            openpyxl.load_workbook(xlsx_path).close()

            log(f"Excel (.xlsx) saved -> {xlsx_path} ({xlsx_path.stat().st_size} bytes)")
            return xlsx_path
        except Exception as exc:
            last_err = exc
            csv_tmp.unlink(missing_ok=True)
            log(f"Download try {attempt}/3 fail: {exc}")
            time.sleep(2)

    raise FlowError(f"Excel download failed: {last_err}")


def needs_logout(page: Page) -> bool:
    if page.is_closed():
        return False
    return not is_login_page(page)


def click_envelope_arrow(page: Page) -> bool:
    """Envelope ke bagal chhote arrow par click."""
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)

    for sel in [
        "li.dropdown:has(.fa-envelope) i.fa-angle-down",
        ".fa-envelope + i.fa-angle-down",
        ".fa-envelope ~ i.fa-angle-down",
        "a:has(.fa-envelope) i.fa-angle-down",
        "i.fa-envelope + i.fa-angle-down",
    ]:
        loc = page.locator(sel).first
        try:
            if loc.is_visible(timeout=1500):
                loc.click()
                time.sleep(1.2)
                log(f"Arrow click: {sel}")
                return True
        except Exception:
            continue

    for sel in ["i.fa-envelope", ".fa-envelope", "span.fa-envelope"]:
        env = page.locator(sel).first
        try:
            if env.is_visible(timeout=2000):
                box = env.bounding_box()
                if box:
                    x = box["x"] + box["width"] + 14
                    y = box["y"] + box["height"] / 2
                    page.mouse.click(x, y)
                    time.sleep(1.2)
                    log("Envelope ke bagal arrow click (mouse)")
                    return True
        except Exception:
            continue

    return click_top_right_menu(page)


def click_top_right_menu(page: Page) -> bool:
    arrows = page.locator("i.fa-angle-down, i.fa-caret-down, i.fa-chevron-down")
    best_idx = -1
    best_x = -1.0
    for i in range(arrows.count()):
        el = arrows.nth(i)
        try:
            if not el.is_visible(timeout=500):
                continue
            box = el.bounding_box()
            if box and box["y"] < 150 and box["x"] > best_x:
                best_x = box["x"]
                best_idx = i
        except Exception:
            continue
    if best_idx >= 0:
        arrows.nth(best_idx).click()
        time.sleep(1)
        return True
    return False


def click_logout_option(page: Page) -> bool:
    try:
        page.wait_for_selector("text=change password", timeout=8000)
    except Exception:
        pass

    for sel in [
        "ul.dropdown-menu li:has-text('logout') a",
        "ul.dropdown-menu >> text=logout",
        ".dropdown-menu >> text=logout",
        "li:has-text('logout')",
        "a:has-text('logout')",
        "span:has-text('logout')",
    ]:
        loc = page.locator(sel).last
        try:
            if loc.is_visible(timeout=2000):
                loc.click(force=True)
                time.sleep(2.5)
                return True
        except Exception:
            continue

    try:
        page.get_by_text("logout", exact=True).last.click(force=True, timeout=3000)
        time.sleep(2.5)
        return True
    except Exception:
        return False


def do_ui_logout(page: Page) -> bool:
    log("Logout: envelope arrow -> logout...")
    if not click_envelope_arrow(page):
        log("Arrow click fail — retry...")
        return False
    if not click_logout_option(page):
        log("logout option nahi mila...")
        return False
    try:
        page.wait_for_selector(USER_SEL, state="visible", timeout=20000)
    except Exception:
        time.sleep(2)
    if is_login_page(page):
        log("Logout OK — login page")
        return True
    return is_login_page(page)


def try_api_logout(page: Page) -> bool:
    """Cloud/headless fallback — sirf auto mode mein UI fail hone par."""
    log("Logout API fallback...")
    try:
        result = page.evaluate(
            """async (url) => {
                const r = await fetch(url, { method: 'GET', credentials: 'include' });
                return { status: r.status, body: await r.text() };
            }""",
            LOGOUT_API,
        )
        log(f"Logout API response: {result}")
        time.sleep(2)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(USER_SEL, state="visible", timeout=20000)
        return is_login_page(page)
    except Exception as exc:
        log(f"Logout API fail: {exc}")
        return False


def mandatory_logout(page: Page) -> None:
    """Logout confirm hone tak — script yahi rukegi. Chrome cut NAHI."""
    if not needs_logout(page):
        return

    auto = os.environ.get("COOPS_AUTO") == "1"
    interactive = (not auto) and sys.stdin.isatty()
    max_tries = 12 if interactive else 20

    log("=" * 50)
    log("AB LOGOUT HOGA — Chrome tab cut NAHI hoga")
    log("=" * 50)

    for n in range(1, max_tries + 1):
        log(f"Logout try {n}/{max_tries}...")
        if do_ui_logout(page):
            return
        time.sleep(1.5)
        page.keyboard.press("Escape")
        time.sleep(0.5)

    if auto and try_api_logout(page):
        log("Logout OK via API fallback")
        return

    if interactive:
        while needs_logout(page):
            log("Auto logout fail — khud karo: arrow -> logout")
            input("Logout ke baad Enter dabao...")
            if is_login_page(page):
                return
            do_ui_logout(page)
    elif needs_logout(page):
        raise FlowError("Logout confirm nahi hua (auto mode)")

    if not is_login_page(page):
        raise FlowError("Logout confirm nahi hua")


def logout_confirmed(page: Page | None) -> bool:
    if not page or page.is_closed():
        return False
    return is_login_page(page)


def setup_downloads(context: BrowserContext) -> None:
    """Sirf accept_downloads — CDP/backup handler NAHI (UUID file bug fix)."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Downloads folder: {DOWNLOAD_DIR}")


def create_context(browser, *, accept_downloads: bool = True, headless: bool = False) -> BrowserContext:
    if headless:
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=accept_downloads,
        )
    else:
        context = browser.new_context(no_viewport=True, accept_downloads=accept_downloads)
    context.add_init_script(CAPTCHA_HOOK)
    return context


def finish_and_close(page: Page | None, browser, logged_in: bool) -> None:
    """Logout confirm -> phir browser band. Direct cut NAHI."""
    if not browser:
        return

    if page and not page.is_closed() and logged_in and needs_logout(page):
        mandatory_logout(page)

    if logged_in and not logout_confirmed(page):
        raise FlowError("Logout confirm nahi hua — browser band nahi kiya")

    log("Logout OK — browser band ho raha hai")
    try:
        browser.close()
    except Exception:
        pass


def try_logout(page: Page) -> bool:
    try:
        mandatory_logout(page)
        return True
    except FlowError:
        return is_login_page(page)


def run_flow(
    login_id: str = LOGIN_ID,
    password: str = PASSWORD,
    *,
    keep_open: bool = True,
    skip_download: bool = False,
    download_dir: Path | None = None,
    headless: bool = False,
) -> Path | None:
    started = time.time()
    browser = None
    page = None
    report_path = None
    logged_in = False
    pw = sync_playwright().start()
    target_dir = download_dir or DOWNLOAD_DIR

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        cleanup_bad_downloads()
        launch_args = ["--disable-popup-blocking"]
        if not headless:
            launch_args.insert(0, "--start-maximized")
        launch_kwargs: dict = {"headless": headless, "args": launch_args}
        if os.name == "nt":
            launch_kwargs["channel"] = "chrome"
        browser = pw.chromium.launch(**launch_kwargs)
        context = create_context(browser, headless=headless)
        page = context.new_page()
        setup_downloads(context)

        do_login(page, login_id, password)
        logged_in = True

        open_dct_status_summary(page)

        if not skip_download:
            report_path = download_dct_excel_report(page, target_dir)
            log(f"Excel (.xlsx) ready: {report_path}")

        log("Download done — AB LOGOUT hoga (arrow -> logout)...")
        mandatory_logout(page)

        log(f"Complete in {time.time() - started:.1f}s")

        if keep_open:
            log("Sab ho gaya. Enter dabao browser band karne ke liye...")
            input()

        finish_and_close(page, browser, logged_in)

    except Exception as exc:
        log(f"Error: {exc}")
        if page and not page.is_closed() and (logged_in or is_logged_in(page)):
            logged_in = True
            log("Error ke baad bhi logout zaroori hai...")
            mandatory_logout(page)
            finish_and_close(page, browser, logged_in)
        elif browser and not logged_in:
            try:
                browser.close()
            except Exception:
                pass
        raise
    finally:
        pw.stop()

    return report_path


def run(login_id: str = LOGIN_ID, password: str = PASSWORD, keep_open: bool = True) -> None:
    run_flow(login_id, password, keep_open=keep_open, skip_download=True)


if __name__ == "__main__":
    lid = sys.argv[1] if len(sys.argv) > 1 else LOGIN_ID
    pwd = sys.argv[2] if len(sys.argv) > 2 else PASSWORD
    run_flow(lid, pwd, keep_open=True)
