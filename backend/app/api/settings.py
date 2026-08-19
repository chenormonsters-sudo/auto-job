import json

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class FingerprintRequest(BaseModel):
    enabled: bool


@router.post("/fingerprint")
def set_fingerprint(payload: FingerprintRequest):
    settings.fingerprint_spoofing_enabled = payload.enabled
    path = settings.data_dir / "runtime_settings.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["fingerprint_spoofing_enabled"] = payload.enabled
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {"fingerprint_spoofing_enabled": payload.enabled}
