import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Resume Job Workbench"
    data_dir: Path = Path("data")
    database_url: str = "sqlite:///./data/workbench.db"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    min_delivery_interval_seconds: int = 40
    max_upload_bytes: int = 10 * 1024 * 1024
    fingerprint_spoofing_enabled: bool = False
    browser_headless: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "uploads").mkdir(parents=True, exist_ok=True)

_runtime_settings_path = settings.data_dir / "runtime_settings.json"
if _runtime_settings_path.exists():
    try:
        _runtime = json.loads(_runtime_settings_path.read_text(encoding="utf-8"))
        settings.fingerprint_spoofing_enabled = bool(_runtime.get("fingerprint_spoofing_enabled", False))
    except Exception:
        pass
