"""アプリケーション設定"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"  # gpt-4.1が利用可能になったらgpt-4.1に変更
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sales_support"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/sales_support"
    
    # App Settings
    debug: bool = True
    log_level: str = "DEBUG"
    app_env: str = "development"
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """設定のシングルトンを取得"""
    return Settings()
