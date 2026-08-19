import threading

from ..config import settings
from ..database import SessionLocal
from ..models import PlatformAccount

LOGIN_URLS = {
    "boss": "https://www.zhipin.com/web/user/?ka=header-login",
    "liepin": "https://www.liepin.com/login/",
    "zhilian": "https://passport.zhaopin.com/login?service=https%3A%2F%2Fwww.zhaopin.com%2F",
    "job51": "https://login.51job.com/login.php",
}

_login_threads: dict[str, threading.Thread] = {}


def _profile_dir(platform: str):
    path = settings.data_dir / "profiles" / platform
    path.mkdir(parents=True, exist_ok=True)
    return path


def _finish(platform: str, profile_path: str, configured: bool) -> None:
    db = SessionLocal()
    try:
        account = db.query(PlatformAccount).filter(PlatformAccount.platform == platform).first()
        if not account:
            account = PlatformAccount(platform=platform)
            db.add(account)
        account.profile_path = profile_path
        account.login_method = "qr"
        account.status = "configured" if configured else "unconfigured"
        db.commit()
    finally:
        db.close()


def _run_qr_login(platform: str) -> None:
    from playwright.sync_api import sync_playwright

    profile_path = str(_profile_dir(platform))
    closed = threading.Event()
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                "window.chrome = window.chrome || {runtime: {}};"
            )
            context.add_init_script(
                """
                window.addEventListener('keydown', (event) => {
                  if (event.key === 'F12') {
                    event.stopImmediatePropagation();
                  }
                }, true);
                """
            )
            if settings.fingerprint_spoofing_enabled:
                context.add_init_script(
                    """
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                    """
                )
            context.on("close", lambda: closed.set())
            page = context.new_page()
            page.goto(LOGIN_URLS[platform], wait_until="domcontentloaded", timeout=30000)
            closed.wait(timeout=180)
            try:
                context.close()
            except Exception:
                pass
        _finish(platform, profile_path, configured=closed.is_set())
    except Exception:
        _finish(platform, profile_path, configured=False)
    finally:
        _login_threads.pop(platform, None)


def start_qr_login(platform: str) -> str:
    thread = _login_threads.get(platform)
    if thread and thread.is_alive():
        return "running"
    thread = threading.Thread(target=_run_qr_login, args=(platform,), daemon=True)
    _login_threads[platform] = thread
    thread.start()
    return "started"


def qr_login_status(platform: str) -> dict:
    thread = _login_threads.get(platform)
    return {
        "platform": platform,
        "running": bool(thread and thread.is_alive()),
    }
