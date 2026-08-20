from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResumeOut(ApiModel):
    id: int
    filename: str
    status: str
    structured_json: dict[str, Any] = {}
    created_at: datetime


class JobCreate(BaseModel):
    platform: str = "manual"
    company: str = ""
    title: str = ""
    url: str = ""
    jd_text: str


class JobSearchRequest(BaseModel):
    platform: str = "boss"
    keyword: str
    city: str = ""


class JobImportItem(BaseModel):
    platform: str
    company: str = ""
    title: str
    url: str


class JobImportRequest(BaseModel):
    items: list[JobImportItem]


class JobOut(ApiModel):
    id: int
    platform: str
    company: str
    title: str
    url: str
    match_score: int | None
    created_at: datetime


class MatchRequest(BaseModel):
    resume_id: int


class PacketRequest(BaseModel):
    resume_id: int
    allow_llm: bool = False


class PacketOut(BaseModel):
    application_id: int
    job_id: int
    resume_id: int
    greeting: str
    resume_version: str


class ApplicationOut(ApiModel):
    id: int
    resume_id: int
    job_id: int
    greeting: str
    status: str
    result_json: dict[str, Any] = {}
    job_url: str = ""
    job_title: str = ""
    job_company: str = ""
    created_at: datetime


class ConfirmSelection(BaseModel):
    application_ids: list[int]
    confirmed: bool = True


class DryRunRequest(BaseModel):
    application_ids: list[int]


class ConfirmDeliveryRequest(BaseModel):
    application_ids: list[int]


class DeliveryItemResult(BaseModel):
    application_id: int
    platform: str
    status: str
    message: str


class DeliveryResult(BaseModel):
    task_id: int
    dry_run: bool
    results: list[DeliveryItemResult]


class PlatformOut(ApiModel):
    platform: str
    login_method: str
    status: str
    expires_at: datetime | None = None


class PlatformAccountIn(BaseModel):
    login_method: str = "qr"
    profile_path: str = ""
    cookie: str = ""
    expires_at: datetime | None = None


class PlatformAccountOut(BaseModel):
    platform: str
    login_method: str
    status: str
    profile_path: str = ""
    has_cookie: bool = False
    expires_at: datetime | None = None
