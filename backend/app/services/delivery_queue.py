import json
import time
from datetime import datetime

from sqlalchemy.orm import Session

from ..adapters import get_adapter
from ..config import settings
from ..models import Application, DeliveryTask, PlatformAccount
from ..services.encryption import decrypt_text


class RateLimitError(RuntimeError):
    pass


def _minimum_interval() -> int:
    return max(20, settings.min_delivery_interval_seconds)


def create_delivery_task(
    db: Session,
    application_ids: list[int],
    dry_run: bool,
) -> DeliveryTask:
    task = DeliveryTask(
        dry_run=1 if dry_run else 0,
        status="pending",
        confirmed_at=datetime.utcnow() if not dry_run else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def finalize_delivery_task(task: DeliveryTask, results: list[dict]) -> None:
    task.logs_json = json.dumps(
        [f"[{item['application_id']}] {item['status']}: {item['message']}" for item in results],
        ensure_ascii=False,
    )
    task.status = "completed" if all(item["status"] in {"ok", "delivered"} for item in results) else "failed"


def run_dry_run(db: Session, application_ids: list[int]) -> list[dict]:
    results = []
    for application_id in application_ids:
        app = db.get(Application, application_id)
        if not app:
            results.append(
                {"application_id": application_id, "status": "failed", "message": "投递项不存在"}
            )
            continue
        job = app.job
        if job.platform == "manual":
            result = {"ok": True, "message": "手动模式：仅生成投递包，不执行自动投递"}
        else:
            try:
                adapter = get_adapter(job.platform)
                account = db.query(PlatformAccount).filter(PlatformAccount.platform == job.platform).first()
                result = adapter.dry_run(
                    application_id,
                    app.greeting,
                    job_url=job.url or "",
                    resume_text=decrypt_text(app.resume_version),
                    profile_path=account.profile_path if account else "",
                    cookie=decrypt_text(account.cookie_ref) if account and account.cookie_ref else "",
                )
            except (KeyError, ValueError) as exc:
                result = {"ok": False, "message": f"平台适配器不可用: {exc}"}
        results.append(
            {
                "application_id": application_id,
                "platform": job.platform,
                "status": "ok" if result.get("ok") else "failed",
                "message": result.get("message", ""),
            }
        )
    return results


def confirm_and_execute(db: Session, application_ids: list[int]) -> list[dict]:
    minimum = _minimum_interval()
    results = []
    for index, application_id in enumerate(application_ids):
        if index > 0:
            time.sleep(minimum)
        app = db.get(Application, application_id)
        if not app:
            results.append(
                {"application_id": application_id, "platform": "?", "status": "failed", "message": "投递项不存在"}
            )
            continue
        if app.status != "confirmed":
            results.append(
                {
                    "application_id": application_id,
                    "platform": app.job.platform,
                    "status": "failed",
                    "message": "该投递项尚未二次确认",
                }
            )
            continue
        if app.job.platform == "manual":
            app.status = "delivered"
            app.result_json = json.dumps({"mode": "manual"}, ensure_ascii=False)
            results.append(
                {
                    "application_id": application_id,
                    "platform": app.job.platform,
                    "status": "delivered",
                    "message": "手动模式：请按投递包自行投递",
                }
            )
            db.add(app)
            continue

        try:
            adapter = get_adapter(app.job.platform)
        except (KeyError, ValueError) as exc:
            app.status = "failed"
            app.result_json = json.dumps({"error": str(exc)}, ensure_ascii=False)
            results.append(
                {
                    "application_id": application_id,
                    "platform": app.job.platform,
                    "status": "failed",
                    "message": str(exc),
                }
            )
            db.add(app)
            continue
        try:
            account = db.query(PlatformAccount).filter(PlatformAccount.platform == app.job.platform).first()
            result = adapter.apply(
                application_id,
                app.greeting,
                job_url=app.job.url or "",
                resume_text=decrypt_text(app.resume_version),
                profile_path=account.profile_path if account else "",
                cookie=decrypt_text(account.cookie_ref) if account and account.cookie_ref else "",
            )
            if not result.get("ok"):
                raise ValueError(result.get("message", "投递失败"))
            app.status = "delivered"
            app.result_json = json.dumps(result, ensure_ascii=False)
            results.append(
                {
                    "application_id": application_id,
                    "platform": app.job.platform,
                    "status": "delivered",
                    "message": "已投递",
                }
            )
        except (NotImplementedError, ValueError) as exc:
            app.status = "failed"
            app.result_json = json.dumps({"error": str(exc)}, ensure_ascii=False)
            results.append(
                {
                    "application_id": application_id,
                    "platform": app.job.platform,
                    "status": "failed",
                    "message": str(exc),
                }
            )
        db.add(app)
    db.commit()
    return results
