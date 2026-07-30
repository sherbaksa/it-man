"""
Pydantic-схемы Repair (ремонт/обслуживание оборудования) — по п. 3.4 и п. 4.2 ТЗ.

RepairCreate — тело POST /api/assets/{asset_id}/repairs. Новая запись всегда
    стартует со status=planned (устанавливается сервисным слоем, не клиентом).
RepairUpdate — тело PATCH /api/repairs/{id}. Все поля опциональны (exclude_unset).
    status здесь — то, через что запускаются переходы planned→in_progress→done/cancelled;
    допустимость перехода проверяется в repair_service.update_repair().
RepairRead — тело ответа.

executor_espocrm_id пока не используется на практике (интеграция с EspoCRM — B17),
но присутствует в схеме, чтобы не менять контракт API позже.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.repair import RepairStatus


class RepairCreate(BaseModel):
    repair_type: str
    cost: Decimal | None = None
    executor: str | None = None
    started_at: datetime | None = None


class RepairUpdate(BaseModel):
    """Частичное обновление ремонта. Передавая status, инициируем переход —
    допустимые переходы: planned→in_progress→done/cancelled (см. repair_service)."""

    repair_type: str | None = None
    cost: Decimal | None = None
    executor: str | None = None
    executor_espocrm_id: str | None = None
    status: RepairStatus | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RepairRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    repair_type: str
    cost: Decimal | None
    executor: str | None
    executor_espocrm_id: str | None
    status: RepairStatus
    started_at: datetime | None
    finished_at: datetime | None
