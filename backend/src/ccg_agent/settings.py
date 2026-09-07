from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_version: str = "0.1.0-dev"
    database_url: str = "sqlite+pysqlite:///./.runtime/ccg.sqlite3"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "song-local:latest"
    allow_cloud: bool = Field(default=False)
    cors_origins: str = "http://localhost:5173"
    project_root: Path = Path(__file__).resolve().parents[3]
    max_source_bytes: int = 2_000_000
    max_media_bytes: int = 25_000_000
    max_media_duration_seconds: float = 180.0
    max_video_width: int = 3840
    max_video_height: int = 3840
    max_video_frames: int = 10_800
    asr_provider: str = "fixture"

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def runtime_root(self) -> Path:
        return self.project_root / ".runtime"


@lru_cache
def get_settings() -> Settings:
    return Settings()
