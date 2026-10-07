from functools import lru_cache
from decimal import Decimal
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_DATA = PROJECT_ROOT / "data"
DEMO_DATABASE_URL = "sqlite:///" + (DEMO_DATA / "noams-demo.db").as_posix()


class Settings(BaseSettings):
    app_name: str = "NOAMS"
    app_env: str = "demo"
    app_debug: bool = False
    database_url: str = DEMO_DATABASE_URL
    log_level: str = "INFO"
    noams_max_upload_bytes: int = 10_485_760
    noams_unusual_min_history: int = 3
    noams_unusual_multiplier: Decimal = Decimal("3")
    noams_unusual_min_difference: Decimal = Decimal("500")
    noams_approval_threshold: Decimal = Decimal("5000")
    noams_split_window_days: int = 3
    noams_split_min_operations: int = 2
    noams_upload_dir: Path = DEMO_DATA / "uploads"

    @field_validator("database_url")
    @classmethod
    def isolate_demo_database(cls, value: str) -> str:
        if value != DEMO_DATABASE_URL:
            raise ValueError("The demo database is fixed to its own data directory.")
        return value

    @field_validator("noams_upload_dir")
    @classmethod
    def isolate_demo_uploads(cls, value: Path) -> Path:
        resolved = (PROJECT_ROOT / value).resolve()
        if not resolved.is_relative_to(DEMO_DATA.resolve()) or resolved == DEMO_DATA.resolve():
            raise ValueError("Demo uploads must stay inside the demo data directory.")
        return resolved

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
