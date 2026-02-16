"""Main FastAPI application (Vertex backend, no observability instrumentation)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import chat_router, plan_router


settings = get_settings()

app = FastAPI(
    title="営業出張サポートAI（Vertex AI版）",
    description="Vertex AI (Gemini) の function calling を使った出張計画サポートAPIです。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(plan_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}

