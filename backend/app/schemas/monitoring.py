"""
Pydantic-схемы мониторинга (MonitoringStatus) — по п. 3.8 и п. 4.5 ТЗ.

MonitoringStatusRead — элемент списка/детали текущего статуса хоста.
MonitoringStatusListResponse — обёртка {items, total} для GET /api/monitoring/status
    (без пагинации/фильтров — ТЗ п. 4.5 не документирует query-параметры для
    этого эндпоинта, в отличие от /api/assets; ожидаемый объём — все хосты
    организации, не тысячи записей).
MonitoringHistoryPoint / MonitoringHistoryResponse — история статусов хоста
    за период для GET /api/monitoring/status/{host_identifier}/history.
MonitoringSummary — агрегат для дашборда руководства, GET /api/monitoring/summary.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource


class MonitoringAssetBrief(BaseModel):
    """Вложенный актив — минимальный набор полей, по аналогии с TicketAssetBrief."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_number: str
    model: str | None


class MonitoringStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    host_identifier: str
    status: MonitoringHealthStatus
    last_value: str | None
    source: MonitoringSource
    checked_at: datetime
    asset: MonitoringAssetBrief | None


class MonitoringStatusListResponse(BaseModel):
    """Обёртка {items, total} для GET /api/monitoring/status."""

    items: list[MonitoringStatusRead]
    total: int


class MonitoringHistoryPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: MonitoringHealthStatus
    last_value: str | None
    checked_at: datetime


class MonitoringHistoryResponse(BaseModel):
    """Ответ GET /api/monitoring/status/{host_identifier}/history."""

    host_identifier: str
    items: list[MonitoringHistoryPoint]


class MonitoringSummary(BaseModel):
    """Агрегат для дашборда руководства, GET /api/monitoring/summary.

    ok/warning/critical — контракт по ТЗ п. 4.5; unknown — добавлено сверх
    контракта, чтобы хосты без свежих данных не терялись молча из подсчёта.
    """

    ok: int
    warning: int
    critical: int
    unknown: int
