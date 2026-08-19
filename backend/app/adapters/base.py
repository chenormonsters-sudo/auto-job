import tempfile
import time
from abc import ABC
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import urlparse

from ..config import settings

try:
    from playwright.sync_api import sync_playwright

    _HAS_PLAYWRIGHT = True
except Exception:  # playwright optional until user installs it
    _HAS_PLAYWRIGHT = False

_FIELD_SELECTORS = [
    "textarea",
    "[contenteditable='true']",
    "div[contenteditable='true']",
    "input[type='text']",
]

_DEFAULT_SUBMIT_KEYWORDS = ["发送", "提交", "立即沟通", "打招呼", "投递", "立即应聘"]


def normalize_cookie_header(value: str) -> str:
    lines = value.replace("\r\n", "\n").split("\n")
    parts = []
    for line in lines:
        line = line.strip()
        if "=" not in line:
            continue
        parts.append(line)
    normalized = "; ".join(parts).strip()
    if normalized.lower().startswith("cookie:"):
        normalized = normalized[7:].strip()
    return normalized


def _parse_cookies(value: str, fallback_host: str) -> list[dict[str, Any]]:
    jar = SimpleCookie()
    try:
        jar.load(normalize_cookie_header(value))
    except Exception:
        return []
    fallback_domain = urlparse(fallback_host).hostname or ""
    cookies = []
    for morsel in jar.values():
        domain = morsel.get("domain") or fallback_domain
        if domain.startswith("."):
            domain = domain[1:]
        if not domain:
            continue
        cookies.append(
            {
                "name": morsel.key,
                "value": morsel.value,
                "domain": domain,
                "path": morsel.get("path") or "/",
            }
        )
    return cookies


class BaseAdapter(ABC):
    name: str = ""
    submit_keywords: list[str] = _DEFAULT_SUBMIT_KEYWORDS

    def login_status(self) -> dict[str, Any]:
        return {"platform": self.name, "status": "unconfigured"}

    def dry_run(
        self,
        application_id: int,
        greeting: str,
        job_url: str = "",
        resume_text: str = "",
        profile_path: str = "",
        cookie: str = "",
    ) -> dict[str, Any]:
        return self._browser_run(
            application_id,
            greeting,
            job_url=job_url,
            resume_text=resume_text,
            profile_path=profile_path,
            cookie=cookie,
            submit=False,
        )

    def apply(
        self,
        application_id: int,
        greeting: str,
        job_url: str = "",
        resume_text: str = "",
        profile_path: str = "",
        cookie: str = "",
    ) -> dict[str, Any]:
        return self._browser_run(
            application_id,
            greeting,
            job_url=job_url,
            resume_text=resume_text,
            profile_path=profile_path,
            cookie=cookie,
            submit=True,
        )

    def _browser_run(
        self,
        application_id: int,
        greeting: str,
        job_url: str,
        resume_text: str,
        profile_path: str,
        cookie: str,
        submit: bool,
    ) -> dict[str, Any]:
        if not _HAS_PLAYWRIGHT:
            return {"ok": False, "message": "后端未安装 playwright，请先安装 Python playwright 依赖"}
        if not job_url:
            return {"ok": False, "message": "职位 URL 未填写，无法执行浏览器投递"}

        user_data_dir = profile_path or tempfile.mkdtemp(prefix="resume-job-browser-")
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel="chrome",
                    headless=settings.browser_headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                    "window.chrome = window.chrome || {runtime: {}};"
                )
                if settings.fingerprint_spoofing_enabled:
                    context.add_init_script(
                        """
                        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                        """
                    )
                if cookie and not profile_path:
                    parsed = _parse_cookies(cookie, job_url)
                    if parsed:
                        context.add_cookies(parsed)
                page = context.new_page()
                page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                deadline = time.time() + 120
                while time.time() < deadline:
                    try:
                        body_text = page.locator("body").inner_text(timeout=5000)
                    except Exception:
                        break
                    page_url = page.url
                    if page_url.startswith("about:blank") or page_url.startswith("chrome://"):
                        return {
                            "ok": False,
                            "message": "平台安全脚本将页面重置为空白页，通常表示自动化操作被识别，请稍后重试或改用真实浏览器登录态",
                            "page_url": page_url,
                        }
                    verifying = (
                        "安全验证" in body_text
                        or "完成验证" in body_text
                        or "security.html" in page_url
                        or "_security_check=" in page_url
                    )
                    if not verifying:
                        break
                    page.wait_for_timeout(2000)

                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                try:
                    page.wait_for_selector(
                        "textarea, [contenteditable='true'], input[type='text']",
                        timeout=15000,
                    )
                except Exception:
                    pass

                field = self._find_greeting_field(page)
                if field is None:
                    shot_dir = settings.data_dir / "screenshots"
                    shot_dir.mkdir(parents=True, exist_ok=True)
                    shot = shot_dir / f"application-{application_id}-debug.png"
                    try:
                        page.screenshot(path=str(shot))
                    except Exception:
                        pass
                    body_text = ""
                    try:
                        body_text = page.locator("body").inner_text(timeout=5000)[:300]
                    except Exception:
                        pass
                    return {
                        "ok": False,
                        "message": "未能进入可投递的职位详情页（可能仍停留在平台安全验证），请稍后重试",
                        "screenshot": str(shot),
                        "body_text": body_text,
                        "page_url": page.url,
                    }
                field.fill(greeting)

                shot_dir = settings.data_dir / "screenshots"
                shot_dir.mkdir(parents=True, exist_ok=True)
                shot = shot_dir / f"application-{application_id}.png"
                page.screenshot(path=str(shot))
                if not submit:
                    return {
                        "ok": True,
                        "mode": "dry_run",
                        "screenshot": str(shot),
                        "message": "已打开职位页并填入打招呼语，未提交",
                    }

                button = self._find_submit_button(page)
                if button is None:
                    return {
                        "ok": False,
                        "message": "已填入打招呼语，但未找到发送按钮，未提交",
                        "screenshot": str(shot),
                    }
                button.click()
                page.wait_for_timeout(3000)
                return {
                    "ok": True,
                    "mode": "apply",
                    "screenshot": str(shot),
                    "message": "已提交打招呼语",
                }
        except Exception as exc:
            return {"ok": False, "message": f"浏览器投递失败: {type(exc).__name__}"}

    def _find_greeting_field(self, page):
        for selector in _FIELD_SELECTORS:
            for locator in page.locator(selector).all():
                try:
                    if locator.is_visible() and locator.is_enabled():
                        return locator
                except Exception:
                    continue
        return None

    def _find_submit_button(self, page):
        for keyword in self.submit_keywords:
            for locator in page.get_by_role("button", name=keyword).all():
                try:
                    if locator.is_visible() and locator.is_enabled():
                        return locator
                except Exception:
                    continue
        return None
