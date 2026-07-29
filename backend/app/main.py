"""
Точка входа FastAPI-приложения "Платформа управления IT-инфраструктурой".

Роутеры по доменам подключаются здесь по мере готовности сессий:
- auth (B03) — подключён
- users (B04) — подключён
- assets (B06) — подключён
- tickets, orders, monitoring — в следующих сессиях
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.core.config import settings

app = FastAPI(
    title="IT Infrastructure Platform API",
    description="Веб-приложение для управления IT-инфраструктурой медицинской организации",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Проверка доступности сервиса (используется docker-compose healthcheck и мониторингом)."""
    return {"status": "ok"}
