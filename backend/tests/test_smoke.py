from fastapi.testclient import TestClient

from app.adapters.boss import BossAdapter
from app.database import SessionLocal
from app.main import app
from app.models import PlatformAccount
from app.services.job_scraper import _relevance_score

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_job():
    resp = client.post(
        "/api/jobs",
        json={
            "platform": "boss",
            "company": "示例公司",
            "title": "后端工程师",
            "jd_text": "熟悉 Python 和 FastAPI",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "后端工程师"


def test_platform_cookie_is_encrypted():
    resp = client.put(
        "/api/platforms/job51/account",
        json={"login_method": "cookie", "cookie": "session=plain-secret; Domain=example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["has_cookie"] is True

    row = SessionLocal().query(PlatformAccount).filter(PlatformAccount.platform == "job51").first()
    assert row is not None
    assert "plain-secret" not in row.cookie_ref
    assert row.cookie_ref.startswith("gAAAA")

    client.delete("/api/platforms/job51/account")


def test_browser_adapter_requires_job_url():
    result = BossAdapter().dry_run(1, "您好")
    assert result["ok"] is False
    assert "URL" in result["message"]


def test_search_relevance_filter():
    assert _relevance_score("后端工程师", {"title": "Java后端开发工程师", "company": ""}) >= 90
    assert _relevance_score("后端工程师", {"title": "AI大模型工程师", "company": ""}) < 90
    assert _relevance_score("测试", {"title": "AI测试开发", "company": ""}) >= 90
    assert _relevance_score("Python后端工程师", {"title": "Java后端开发", "company": ""}) < 90
