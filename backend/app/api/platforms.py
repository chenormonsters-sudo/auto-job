import webbrowser

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..adapters import list_adapters
from ..adapters.base import normalize_cookie_header
from ..database import get_db
from ..models import PlatformAccount
from ..schemas import PlatformAccountIn, PlatformAccountOut
from ..services.encryption import decrypt_text, encrypt_text
from ..services.qr_login import LOGIN_URLS, qr_login_status, start_qr_login

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


def _account_out(account: PlatformAccount | None, platform: str) -> PlatformAccountOut:
    return PlatformAccountOut(
        platform=platform,
        login_method=account.login_method if account else "qr",
        status=account.status if account else "unconfigured",
        profile_path=account.profile_path if account else "",
        has_cookie=bool(account and account.cookie_ref),
        expires_at=account.expires_at if account else None,
    )


@router.get("", response_model=list[PlatformAccountOut])
def list_platforms(db: Session = Depends(get_db)):
    accounts = {a.platform: a for a in db.query(PlatformAccount).all()}
    return [_account_out(accounts.get(a.name), a.name) for a in list_adapters()]


@router.post("/{platform}/qr-login")
def open_qr_login(platform: str, db: Session = Depends(get_db)):
    if platform not in {a.name for a in list_adapters()}:
        raise HTTPException(status_code=422, detail=f"不支持的平台: {platform}")
    state = start_qr_login(platform)
    return {"platform": platform, "state": state}


@router.post("/{platform}/open-login")
def open_login_in_default_browser(platform: str, db: Session = Depends(get_db)):
    if platform not in {a.name for a in list_adapters()}:
        raise HTTPException(status_code=422, detail=f"不支持的平台: {platform}")
    webbrowser.open(LOGIN_URLS[platform])
    return {"platform": platform, "opened": True}


@router.get("/{platform}/qr-status")
def read_qr_login_status(platform: str, db: Session = Depends(get_db)):
    if platform not in {a.name for a in list_adapters()}:
        raise HTTPException(status_code=422, detail=f"不支持的平台: {platform}")
    state = qr_login_status(platform)
    account = db.query(PlatformAccount).filter(PlatformAccount.platform == platform).first()
    return {
        "platform": platform,
        "running": state["running"],
        "account_status": account.status if account else "unconfigured",
        "profile_path": account.profile_path if account else "",
    }


@router.put("/{platform}/account", response_model=PlatformAccountOut)
def save_platform_account(
    platform: str,
    payload: PlatformAccountIn,
    db: Session = Depends(get_db),
):
    if platform not in {a.name for a in list_adapters()}:
        raise HTTPException(status_code=422, detail=f"不支持的平台: {platform}")
    if not payload.profile_path.strip() and not payload.cookie.strip():
        raise HTTPException(status_code=400, detail="请提供浏览器用户目录或 Cookie 至少一项")
    normalized_cookie = normalize_cookie_header(payload.cookie.strip()) if payload.cookie.strip() else ""
    if payload.cookie.strip() and not normalized_cookie:
        raise HTTPException(status_code=400, detail="Cookie 格式不正确，请检查后重试")

    account = db.query(PlatformAccount).filter(PlatformAccount.platform == platform).first()
    if not account:
        account = PlatformAccount(platform=platform)
        db.add(account)
    account.login_method = payload.login_method or "qr"
    account.profile_path = payload.profile_path.strip()
    account.cookie_ref = encrypt_text(normalized_cookie) if normalized_cookie else account.cookie_ref
    account.status = "configured"
    account.expires_at = payload.expires_at
    db.commit()
    db.refresh(account)
    return _account_out(account, platform)


@router.delete("/{platform}/account", response_model=PlatformAccountOut)
def clear_platform_account(platform: str, db: Session = Depends(get_db)):
    account = db.query(PlatformAccount).filter(PlatformAccount.platform == platform).first()
    if account:
        account.status = "unconfigured"
        account.login_method = "qr"
        account.profile_path = ""
        account.cookie_ref = ""
        account.expires_at = None
        db.commit()
    return _account_out(account, platform)


def get_platform_account(db: Session, platform: str) -> dict:
    account = db.query(PlatformAccount).filter(PlatformAccount.platform == platform).first()
    if not account or (not account.profile_path and not account.cookie_ref):
        return {"profile_path": "", "cookie": ""}
    return {
        "profile_path": account.profile_path or "",
        "cookie": decrypt_text(account.cookie_ref) if account.cookie_ref else "",
    }
