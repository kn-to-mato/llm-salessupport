"""ロギング設定"""
import logging
import sys
from typing import Any, Dict

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from app.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """ロギングの初期化"""
    
    # ログレベルの設定
    log_level = getattr(logging, settings.log_level.upper(), logging.DEBUG)
    
    # 標準ロガーの設定
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # LangChainのログレベルも設定
    logging.getLogger("langchain").setLevel(log_level)
    logging.getLogger("openai").setLevel(log_level)
    logging.getLogger("httpx").setLevel(logging.INFO)  # httpxは少し抑える
    
    # structlogの設定
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.debug:
        # 開発環境: 読みやすいフォーマット
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # 本番環境: JSON形式
        processors = shared_processors + [
            JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """ロガーを取得"""
    return structlog.get_logger(name)

