from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Job, Resume
from ..services.encryption import decrypt_text
from ..services.llm import LLMError
from ..services.resume_reviewer import review_resume

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/resumes/{resume_id}")
def review(
    resume_id: int,
    job_id: int | None = None,
    allow_llm: bool = False,
    db: Session = Depends(get_db),
):
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    if not allow_llm:
        raise HTTPException(status_code=400, detail="请先确认允许将简历内容发送至云端 AI 后再开始审查")
    job_text = None
    if job_id:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="职位不存在")
        job_text = job.jd_text
    try:
        result = review_resume(decrypt_text(resume.raw_text), job_text)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"resume_id": resume.id, "review": result}
