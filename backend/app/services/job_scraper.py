import tempfile
import time
from difflib import SequenceMatcher
from urllib.parse import quote

import jieba
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

_SCRAPE_JS = r"""
() => {
  const seen = new Set();
  const items = [];
  const clean = (value) => String(value || '').replace(/[\uE000-\uF8FF]/g, '').replace(/\s+/g, ' ').trim();
  const decodeSalary = (value) => String(value || '').replace(/[\uE031-\uE03A]/g, (ch) => String(ch.charCodeAt(0) - 0xE031));
  const firstText = (root, selectors) => {
    for (const selector of selectors) {
      const el = root.querySelector(selector);
      if (el && el.innerText && el.innerText.trim()) return clean(el.innerText);
    }
    return '';
  };
  const cards = [...document.querySelectorAll('li.job-card-box, .job-card-wrap')];
  const links = [...document.querySelectorAll('a[href*="job_detail"]')];
  const nodes = cards.length ? cards : links;
  for (const node of nodes) {
    const card = node.matches('li.job-card-box, .job-card-wrap') ? node : (node.closest('li.job-card-box, .job-card-wrap') || node.parentElement || node);
    const a = node.matches('a[href*="job_detail"]') ? node : card.querySelector('a[href*="job_detail"]');
    if (!a) continue;
    const href = a.href;
    if (!href || seen.has(href)) continue;
    const titleEl = a.querySelector('.job-name') || card.querySelector('.job-name') || a;
    let title = clean(titleEl.innerText || a.innerText || '');
    title = title.replace(/\s*\d+(?:-\d+)?K[·・]?\d*薪?\s*(本科|大专|硕士|博士|不限)?$/i, '').trim();
    if (!title) continue;
    const company = firstText(card, [
      '.company-name', '.boss-name', '.job-card-right .company-info h3',
      '.job-card-right .company-info', 'a[href*="/company/"]'
    ]);
    const salary = decodeSalary(firstText(card, ['.job-salary', '.salary', '[class*="salary"]', '[class*="pay"]']));
    const location = firstText(card, ['.job-area', '.company-location', '.job-address-desc', '.job-location']);
    const tags = [...card.querySelectorAll('.tag-list li, .job-exp, .job-degree, [class*="tag"]')]
      .map((el) => clean(el.innerText))
      .filter(Boolean);
    seen.add(href);
    items.push({ title, company, salary, location, tags: tags.slice(0, 6), url: href });
  }
  return items.slice(0, 30);
}
"""

_GENERIC_KEYWORD_TOKENS = {
    "工程师", "开发", "岗位", "招聘", "专员", "经理", "主管", "实习生", "实习",
    "设计师", "运营", "销售", "客服", "助理", "负责人", "顾问",
}


def _core_keyword_tokens(keyword: str) -> list[str]:
    text = keyword.lower().strip()
    words = [word.strip() for word in jieba.lcut(text) if len(word.strip()) >= 2]
    non_generic = [word for word in words if word not in _GENERIC_KEYWORD_TOKENS]
    if non_generic:
        return non_generic
    bigrams = [text[index : index + 2] for index in range(len(text) - 1)]
    non_generic_bigrams = [bigram for bigram in bigrams if len(bigram) == 2 and bigram not in _GENERIC_KEYWORD_TOKENS]
    return non_generic_bigrams[:1] or ([text] if text else [])


def _relevance_score(keyword: str, item: dict) -> int:
    keyword = keyword.lower().strip()
    title = (item.get("title") or "").lower()
    haystack = f"{title} {item.get('company') or ''}".lower()
    if keyword and keyword in title:
        return 100
    core = _core_keyword_tokens(keyword)
    if not core:
        return 0
    if all(token in haystack for token in core):
        return 100 if all(token in title for token in core) else 92
    if core[0] in title:
        return 92
    if any(token in title for token in core):
        return 80
    if any(token in haystack for token in core):
        return 70
    ratio = SequenceMatcher(None, keyword, title).ratio()
    return 80 if ratio >= 0.6 else 0


def _filter_relevant_items(keyword: str, items: list[dict], min_score: int = 90) -> list[dict]:
    for item in items:
        item["relevance_score"] = _relevance_score(keyword, item)
    return [item for item in items if item.get("relevance_score", 0) >= min_score]


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
        for _ in range(12):
            items = page.evaluate(_SCRAPE_JS)
            if len(items) >= 20:
                break
            try:
                page.evaluate("window.scrollBy(0, 3000)")
            except Exception:
                pass
            page.wait_for_timeout(2000)
        items = _filter_relevant_items(keyword, items)
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
