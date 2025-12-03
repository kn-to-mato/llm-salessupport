"""営業出張サポートAI - メインアプリケーション"""
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import get_settings
from app.logging_config import setup_logging, get_logger
from app.api.routes import chat_router, plan_router

settings = get_settings()

# ロギング初期化
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    logger.info(
        "application_startup",
        env=settings.app_env,
        debug=settings.debug,
        log_level=settings.log_level,
        openai_model=settings.openai_model,
    )
    yield
    logger.info("application_shutdown")


# FastAPIアプリケーション
app = FastAPI(
    title="営業出張サポートAI",
    description="LangChainを使用した出張計画サポートAPIです。",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """リクエスト/レスポンスのログ出力ミドルウェア"""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # リクエストログ
    logger.debug(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_host=request.client.host if request.client else None,
    )
    
    # コンテキストにrequest_idを設定
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    try:
        response = await call_next(request)
        
        # レスポンスログ
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2),
        )
        raise


# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(chat_router)
app.include_router(plan_router)


@app.get("/")
async def root():
    """ヘルスチェック"""
    logger.debug("health_check_root")
    return {
        "message": "営業出張サポートAI API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント"""
    logger.debug("health_check")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
