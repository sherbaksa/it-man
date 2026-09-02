"""
Точка входа FastAPI-приложения "Платформа управления IT-инфраструктурой".

Роутеры по доменам подключаются здесь по мере готовности сессий:
- auth (B03) — подключён
- users (B04) — подключён
- assets (B06) — подключён
- repairs (B08) — подключён
- tickets (B09) — подключён
- my/tickets (B10) — подключён
- equipment-types (B09a) — подключён
- attachments (B10a) — подключён
- ticket-assignees (B10b) — подключён
- orders, monitoring — в следующих сессиях
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assets import router as assets_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.equipment_types import router as equipment_types_router
from app.api.my_tickets import router as my_tickets_router
from app.api.repairs import router as repairs_router
from app.api.ticket_assignees import router as ticket_assignees_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.storage import ensure_bucket_exists

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



@app.on_event("startup")
def _init_storage() -> None:
    """Idempotent-создание бакета MinIO для вложений заявок при старте приложения.

    Обёрнуто в try/except: недоступность MinIO на старте (например, в CI, где
    реальный MinIO сознательно не поднимается — см. план сессии B10a, тесты
    мокают все обращения к MinIO) не должна блокировать запуск всего приложения.
    В реальной эксплуатации (dev/prod) это не маскирует проблему — backend
    стартует после MinIO по healthcheck-зависимости в docker-compose, так что
    сюда мы попадаем уже с реально доступным MinIO."""
    import logging

    try:
        ensure_bucket_exists()
    except Exception as exc:  # noqa: BLE001 — намеренно широкий catch, см. докстринг
        logging.getLogger(__name__).warning("Не удалось создать бакет MinIO при старте: %s", exc)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(assets_router)
app.include_router(equipment_types_router)
app.include_router(attachments_router)
app.include_router(ticket_assignees_router)
app.include_router(my_tickets_router)
app.include_router(repairs_router)
app.include_router(tickets_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Проверка доступности сервиса (используется docker-compose healthcheck и мониторингом)."""
    return {"status": "ok"}
