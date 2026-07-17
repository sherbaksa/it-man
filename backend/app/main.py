"""
Точка входа FastAPI-приложения "Платформа управления IT-инфраструктурой".

На этом этапе (сессия J01) — только скелет приложения с health-check
эндпоинтом, чтобы поднять рабочий каркас через docker compose.
Роутеры по доменам (auth, assets, tickets, orders, monitoring)
будут подключаться в последующих сессиях (см. backend/app/api/).
"""

from fastapi import FastAPI

app = FastAPI(
    title="IT Infrastructure Platform API",
    description="Веб-приложение для управления IT-инфраструктурой медицинской организации",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Проверка доступности сервиса (используется docker-compose healthcheck и мониторингом)."""
    return {"status": "ok"}