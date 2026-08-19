import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Resume
from ..schemas import ResumeOut
from ..services.encryption import encrypt_text
from ..services.resume_parser import ResumeParseError, extract_text

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "resume.txt").suffix
    if suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF、DOCX、TXT、MD 简历")

    stored_path = settings.data_dir / "uploads" / f"{uuid4().hex}{suffix}"
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="简历文件超过大小限制")

    magic = content[:8]
    if suffix == ".pdf" and not magic.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="PDF 文件内容校验失败")
    if suffix == ".docx" and not magic.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail="DOCX 文件内容校验失败")

    stored_path.write_bytes(content)

    try:
        raw_text = extract_text(stored_path)
    except ResumeParseError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resume = Resume(
        filename=file.filename or stored_path.name,
        stored_path=str(stored_path),
        raw_text=encrypt_text(raw_text),
        structured_json=json.dumps({"char_count": len(raw_text)}, ensure_ascii=False),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return ResumeOut(
        id=resume.id,
        filename=resume.filename,
        status=resume.status,
        structured_json=json.loads(resume.structured_json or "{}"),
        created_at=resume.created_at,
    )


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db)):
    rows = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return [
        ResumeOut(
            id=r.id,
            filename=r.filename,
            status=r.status,
            structured_json=json.loads(r.structured_json or "{}"),
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{resume_id}/confirm", response_model=ResumeOut)
def confirm_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    resume.status = "confirmed"
    db.commit()
    db.refresh(resume)
    return ResumeOut(
        id=resume.id,
        filename=resume.filename,
        status=resume.status,
        structured_json=json.loads(resume.structured_json or "{}"),
        created_at=resume.created_at,
    )
