"""データベース設定"""
from sqlalchemy import Column, String, Text, DateTime, JSON, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

from app.config import get_settings

settings = get_settings()

# 非同期エンジン
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# 同期エンジン（Alembic用）
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
)

# セッション
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


class ChatSession(Base):
    """チャットセッションテーブル"""
    __tablename__ = "chat_sessions"
    
    session_id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    conditions = Column(JSON, default={})
    plans = Column(JSON, default=[])
    messages = Column(JSON, default=[])
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


async def get_db():
    """DBセッションを取得"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """データベース初期化"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

