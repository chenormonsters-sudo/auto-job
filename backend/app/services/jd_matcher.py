import re


def simple_match(resume_text: str, jd_text: str) -> int:
    words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9+#.]+", jd_text.lower())
    keywords = [w for w in words if len(w) >= 2]
    if not keywords:
        return 0
    hits = sum(1 for w in set(keywords) if w in resume_text.lower())
    return min(100, round(hits / max(1, len(set(keywords))) * 100))

