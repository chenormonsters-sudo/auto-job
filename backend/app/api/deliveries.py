import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, DeliveryTask
from ..schemas import (
    ApplicationOut,
    ConfirmDeliveryRequest,
    ConfirmSelection,
    DeliveryResult,
    DeliveryItemResult,
    DryRunRequest,
)
from ..services.delivery_queue import (
    RateLimitError,
    confirm_and_execute,
    create_delivery_task,
    finalize_delivery_task,
    run_dry_run,
)

router = APIRouter(prefix="/api", tags=["deliveries"])


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    rows = db.query(Application).order_by(Application.created_at.desc()).all()
    return [
        ApplicationOut(
            id=r.id,
            resume_id=r.resume_id,
            job_id=r.job_id,
            greeting=r.greeting,
            status=r.status,
            result_json=json.loads(r.result_json or "{}"),
            job_url=r.job.url or "",
            job_title=r.job.title or "",
            job_company=r.job.company or "",
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/applications/select")
def select_applications(payload: ConfirmSelection, db: Session = Depends(get_db)):
    rows = db.query(Application).filter(Application.id.in_(payload.application_ids)).all()
    for row in rows:
        row.status = "confirmed" if payload.confirmed else "pending_confirm"
    db.commit()
    return {"updated": len(rows), "confirmed": payload.confirmed}


@router.post("/applications/semi-delivered")
def mark_semi_delivered(payload: ConfirmSelection, db: Session = Depends(get_db)):
    if not payload.application_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个投递项")
    rows = db.query(Application).filter(Application.id.in_(payload.application_ids)).all()
    for row in rows:
        row.status = "semi_delivered"
        row.result_json = json.dumps({"mode": "semi_auto", "manual": True}, ensure_ascii=False)
    db.commit()
    return {"updated": len(rows)}


@router.post("/deliveries/dry-run", response_model=DeliveryResult)
def dry_run(payload: DryRunRequest, db: Session = Depends(get_db)):
    if not payload.application_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个投递项")
    task = create_delivery_task(db, payload.application_ids, dry_run=True)
    results = run_dry_run(db, payload.application_ids)
    finalize_delivery_task(task, results)
    db.add(task)
    db.commit()
    return DeliveryResult(
        task_id=task.id,
        dry_run=True,
        results=[DeliveryItemResult(**item) for item in results],
    )


@router.post("/deliveries/confirm", response_model=DeliveryResult)
def confirm_delivery(payload: ConfirmDeliveryRequest, db: Session = Depends(get_db)):
    if not payload.application_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个投递项")
    task = create_delivery_task(db, payload.application_ids, dry_run=False)
    try:
        results = confirm_and_execute(db, payload.application_ids)
    except RateLimitError as exc:
        task.status = "failed"
        task.logs_json = '["rate limited"]'
        db.add(task)
        db.commit()
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    finalize_delivery_task(task, results)
    db.add(task)
    db.commit()
    return DeliveryResult(
        task_id=task.id,
        dry_run=False,
        results=[DeliveryItemResult(**item) for item in results],
    )


@router.get("/deliveries")
def list_deliveries(db: Session = Depends(get_db)):
    rows = db.query(DeliveryTask).order_by(DeliveryTask.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "dry_run": bool(t.dry_run),
            "status": t.status,
            "confirmed_at": t.confirmed_at,
            "logs": json.loads(t.logs_json or "[]"),
        }
        for t in rows
    ]
