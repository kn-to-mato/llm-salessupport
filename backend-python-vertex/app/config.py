"""Application settings (no observability instrumentation)."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Cloud / Vertex AI
    vertex_enabled: bool = True
    google_cloud_project: str = ""
    google_cloud_location: str = "asia-northeast1"
    vertex_model: str = "gemini-2.5-flash"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

