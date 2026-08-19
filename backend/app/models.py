from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    raw_text = Column(Text, default="")
    structured_json = Column(Text, default="{}")
    status = Column(String, default="draft")  # draft | confirmed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    platform = Column(String, default="manual")
    company = Column(String, default="")
    title = Column(String, default="")
    url = Column(String, default="")
    jd_text = Column(Text, default="")
    parsed_json = Column(Text, default="{}")
    match_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    greeting = Column(Text, default="")
    resume_version = Column(Text, default="")
    status = Column(String, default="pending_confirm")
    result_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resume = relationship("Resume")
    job = relationship("Job")


class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id = Column(Integer, primary_key=True)
    dry_run = Column(Integer, default=1)
    status = Column(String, default="pending")
    confirmed_at = Column(DateTime, nullable=True)
    logs_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id = Column(Integer, primary_key=True)
    platform = Column(String, unique=True, nullable=False)
    login_method = Column(String, default="qr")
    status = Column(String, default="unconfigured")
    cookie_ref = Column(String, default="")
    profile_path = Column(String, default="")
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
