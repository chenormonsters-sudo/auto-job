from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Job, PlatformAccount, Resume
from ..schemas import (
    JobCreate,
    JobImportRequest,
    JobOut,
    JobSearchRequest,
    MatchRequest,
    PacketOut,
    PacketRequest,
)
from ..services.greeting_generator import generate_greeting
from ..services.encryption import decrypt_text, encrypt_text
from ..services.jd_matcher import simple_match
from ..services.job_scraper import search_boss_jobs
from ..services.llm import LLMError

ALLOWED_PLATFORMS = {"boss", "liepin", "zhilian", "job51", "manual"}

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    if payload.platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=422, detail=f"不支持的平台: {payload.platform}")
    if not payload.jd_text.strip():
        raise HTTPException(status_code=422, detail="JD 文本不能为空")
    job = Job(
        platform=payload.platform,
        company=payload.company,
        title=payload.title,
        url=payload.url,
        jd_text=payload.jd_text,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.post("/search")
def search_jobs(payload: JobSearchRequest, db: Session = Depends(get_db)):
    if payload.platform != "boss":
        raise HTTPException(status_code=400, detail="当前只支持 BOSS直聘职位搜索")
    if not payload.keyword.strip():
        raise HTTPException(status_code=422, detail="请输入搜索关键词")
    account = db.query(PlatformAccount).filter(PlatformAccount.platform == payload.platform).first()
    if not account or (not account.profile_path and not account.cookie_ref):
        raise HTTPException(status_code=400, detail="请先在平台页配置该平台账号")
    cookie = decrypt_text(account.cookie_ref) if account.cookie_ref else ""
    return search_boss_jobs(payload.keyword, payload.city, account.profile_path or "", cookie)


@router.post("/import")
def import_jobs(payload: JobImportRequest, db: Session = Depends(get_db)):
    created = []
    skipped = 0
    for item in payload.items:
        if item.platform not in ALLOWED_PLATFORMS:
            raise HTTPException(status_code=422, detail=f"不支持的平台: {item.platform}")
        if not item.url.strip() or not item.title.strip():
            skipped += 1
            continue
        exists = db.query(Job).filter(Job.url == item.url.strip()).first()
        if exists:
            skipped += 1
            continue
        job = Job(
            platform=item.platform,
            company=item.company.strip(),
            title=item.title.strip(),
            url=item.url.strip(),
            jd_text=f"职位：{item.title.strip()}（来自搜索采集）",
        )
        db.add(job)
        created.append(job)
    db.commit()
    return {
        "created": [{"id": j.id, "title": j.title, "company": j.company, "url": j.url} for j in created],
        "skipped": skipped,
    }


@router.post("/{job_id}/match")
def match_job(job_id: int, payload: MatchRequest, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    resume = db.get(Resume, payload.resume_id)
    if not job or not resume:
        raise HTTPException(status_code=404, detail="职位或简历不存在")
    score = simple_match(decrypt_text(resume.raw_text), job.jd_text)
    job.match_score = score
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "match_score": score}


@router.post("/{job_id}/packet", response_model=PacketOut)
def create_packet(job_id: int, payload: PacketRequest, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    resume = db.get(Resume, payload.resume_id)
    if not job or not resume:
        raise HTTPException(status_code=404, detail="职位或简历不存在")
    if not payload.allow_llm:
        raise HTTPException(status_code=400, detail="请先确认允许将简历内容发送至云端 AI 生成打招呼语")

    resume_text = decrypt_text(resume.raw_text)
    try:
        greeting = generate_greeting(job.company, job.title, resume_text, job.jd_text)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=f"打招呼语生成失败: {exc}") from exc
    resume_version = resume_text[:8000]
    app = Application(
        resume_id=resume.id,
        job_id=job.id,
        greeting=greeting,
        resume_version=encrypt_text(resume_version),
        status="pending_confirm",
    )
    db.add(app)
    db.commit()
    return PacketOut(
        application_id=app.id,
        job_id=job.id,
        resume_id=resume.id,
        greeting=greeting,
        resume_version=resume_version,
    )
