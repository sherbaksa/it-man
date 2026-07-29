"""
Pydantic-схемы оборудования (Asset) — по п. 3.2 и п. 4.2 ТЗ.

AssetCreate — тело POST /api/assets.
AssetUpdate — тело PATCH /api/assets/{id} (все поля опциональны; появится в B07).
AssetRead — тело ответа для списка (GET /api/assets), с вложенными
    объектами type/responsible_user вместо голых ID (см. пример в п. 4.2 ТЗ).
AssetDetail — тело ответа для GET /api/assets/{id}, дополнительно с
    movements[]/repairs[].

monitoring_status пока всегда null — реальные данные появятся в сессиях B11-B13
(мониторинг/Zabbix), поле заведено заранее, чтобы не менять контракт для Dev2 позже.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.asset import AssetStatus
from app.models.repair import RepairStatus


class EquipmentTypeBrief(BaseModel):
    """Вложенный тип оборудования — только id/name, без лишних полей."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ResponsibleUserBrief(BaseModel):
    """Вложенный ответственный пользователь — минимальный набор полей для отображения."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class MonitoringStatusBrief(BaseModel):
    """Заглушка под мониторинг (появится в B11-B13). Пока не используется в сервисном слое."""

    model_config = ConfigDict(from_attributes=True)

    status: str


class AssetCreate(BaseModel):
    inventory_number: str
    type_id: uuid.UUID
    serial_number: str | None = None
    model: str | None = None
    purchase_date: date | None = None
    location: str | None = None


class AssetUpdate(BaseModel):
    """Полный набор опциональных полей — используется PATCH-эндпоинтом в сессии B07."""

    inventory_number: str | None = None
    type_id: uuid.UUID | None = None
    serial_number: str | None = None
    model: str | None = None
    purchase_date: date | None = None
    status: AssetStatus | None = None
    location: str | None = None
    responsible_user_id: uuid.UUID | None = None
    ip_address: str | None = None
    hostname: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_number: str
    type: EquipmentTypeBrief
    serial_number: str | None
    model: str | None
    purchase_date: date | None
    status: AssetStatus
    location: str | None
    responsible_user: ResponsibleUserBrief | None
    ip_address: str | None
    hostname: str | None
    monitoring_status: MonitoringStatusBrief | None = None
    created_at: datetime
    updated_at: datetime


class MovementBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_location: str | None
    to_location: str
    initiator: ResponsibleUserBrief
    moved_at: datetime
    comment: str | None


class RepairBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repair_type: str
    cost: Decimal | None
    executor: str | None
    status: RepairStatus
    started_at: datetime | None
    finished_at: datetime | None


class AssetDetail(AssetRead):
    """Ответ GET /api/assets/{id} — расширяет AssetRead историей перемещений и ремонтов."""

    movements: list[MovementBrief]
    repairs: list[RepairBrief]


class AssetListResponse(BaseModel):
    """Обёртка для GET /api/assets — {items, total} по п. 4.2 ТЗ."""

    items: list[AssetRead]
    total: int
