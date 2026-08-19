import tempfile
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from ..adapters.base import _parse_cookies
from ..config import settings

CITY_CODES = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "武汉": "101200100",
    "南京": "101190100",
    "苏州": "101190400",
    "西安": "101110100",
    "重庆": "101040100",
    "长沙": "101250100",
}

_SCRAPE_JS = """
() => {
  const seen = new Set();
  const items = [];
  for (const a of document.querySelectorAll('a[href*="job_detail"]')) {
    const href = a.href;
    if (!href || seen.has(href)) continue;
    const card = a.closest('li, [class*="job-card"], [class*="job-item"], [class*="search-job"]') || a.parentElement;
    const titleEl = a.querySelector('.job-name') || (card && card.querySelector('.job-name')) || a;
    const title = (titleEl.innerText || a.innerText || '').trim().split('\\n')[0];
    if (!title) continue;
    const company = (card && card.querySelector('[class*="company-name"], [class*="company"], a[href*="/company/"]') ? card.querySelector('[class*="company-name"], [class*="company"], a[href*="/company/"]').innerText : '').trim();
    const salary = (card && card.querySelector('.salary, [class*="salary"], [class*="pay"]') ? card.querySelector('.salary, [class*="salary"], [class*="pay"]').innerText : '').trim();
    seen.add(href);
    items.push({ title, company, salary, url: href });
  }
  return items.slice(0, 20);
}
"""


def search_boss_jobs(keyword: str, city: str, profile_path: str = "", cookie: str = "") -> dict:
    city_code = CITY_CODES.get(city.strip(), "")
    city_param = f"&city={city_code}" if city_code else ""
    search_url = f"https://www.zhipin.com/web/geek/job?query={quote(keyword.strip())}{city_param}"
    user_data_dir = profile_path or tempfile.mkdtemp(prefix="resume-job-search-")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--disable-infobars", "--no-first-run"],
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            "window.chrome = window.chrome || {runtime: {}};"
        )
        if cookie and not profile_path:
            parsed = _parse_cookies(cookie, search_url)
            if parsed:
                context.add_cookies(parsed)
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                body_text = page.locator("body").inner_text(timeout=5000)
            except Exception:
                return {"items": [], "search_url": search_url, "body_text": "浏览器窗口已关闭，未完成安全验证"}
            page_url = page.url
            if page_url.startswith("about:blank") or page_url.startswith("chrome://"):
                return {
                    "items": [],
                    "search_url": search_url,
                    "body_text": "平台安全脚本将页面重置为空白页，请稍后重试",
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
            page.wait_for_selector('a[href*="job_detail"]', timeout=20000)
        except Exception:
            pass
        items = []
        for _ in range(10):
            items = page.evaluate(_SCRAPE_JS)
            if items:
                break
            page.wait_for_timeout(2000)
        body_text = ""
        try:
            body_text = page.locator("body").inner_text(timeout=5000)[:300]
        except Exception:
            pass
        shot_dir = settings.data_dir / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot = shot_dir / "job-search.png"
        try:
            page.screenshot(path=str(shot))
        except Exception:
            pass
        context.close()

    return {"items": items, "search_url": search_url, "body_text": body_text, "page_url": page.url}
