"""
API-роуты мониторинга (MonitoringStatus) — по п. 4.5 ТЗ.

GET /api/monitoring/status — список текущих статусов всех хостов, с кэшем в
    Redis (TTL 60с, ключ "monitoring:status:all" — неймспейс зарезервирован
    в плане B12, чтобы не пересекаться с будущим кэшем EspoCRM в B17).
GET /api/monitoring/status/{host_identifier}/history — история из append-only
    журнала MonitoringStatusHistory (добавлен в B12, см. отчёт сессии) за
    период from/to.
GET /api/monitoring/summary — агрегат {ok, warning, critical, unknown} для
    дашборда руководства.

Доступ: Engineer+ (Engineer, IT-Head, Admin) для status/history;
Executive+ (Executive, IT-Head, Admin) для summary — см. п. 1.3 ТЗ.
"""
from typing import cast
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from redis import Redis
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.redis_client import get_redis
from app.models.user import UserRole
from app.schemas.monitoring import (
    MonitoringHistoryPoint,
    MonitoringHistoryResponse,
    MonitoringStatusListResponse,
    MonitoringStatusRead,
    MonitoringSummary,
)
from app.services import monitoring_service

_STATUS_CACHE_KEY = "monitoring:status:all"
_STATUS_CACHE_TTL_SECONDS = 60

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get(
    "/status",
    response_model=MonitoringStatusListResponse,
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)
def get_monitoring_status(
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> MonitoringStatusListResponse:
    cached = redis_client.get(_STATUS_CACHE_KEY)
    if cached is not None:
        return MonitoringStatusListResponse.model_validate_json(cast(str, cached))

    items = monitoring_service.list_current_statuses(db)
    response = MonitoringStatusListResponse(
        items=[MonitoringStatusRead.model_validate(item) for item in items],
        total=len(items),
    )
    redis_client.set(_STATUS_CACHE_KEY, response.model_dump_json(), ex=_STATUS_CACHE_TTL_SECONDS)
    return response


@router.get(
    "/status/{host_identifier}/history",
    response_model=MonitoringHistoryResponse,
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)
def get_monitoring_history(
    host_identifier: str,
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
) -> MonitoringHistoryResponse:
    items = monitoring_service.get_host_history(db, host_identifier, date_from, date_to)
    return MonitoringHistoryResponse(
        host_identifier=host_identifier,
        items=[MonitoringHistoryPoint.model_validate(item) for item in items],
    )


@router.get(
    "/summary",
    response_model=MonitoringSummary,
    dependencies=[Depends(require_role(UserRole.EXECUTIVE, UserRole.IT_HEAD, UserRole.ADMIN))],
)
def get_monitoring_summary(db: Session = Depends(get_db)) -> MonitoringSummary:
    return MonitoringSummary(**monitoring_service.get_summary(db))
