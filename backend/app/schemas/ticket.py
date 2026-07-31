"""
Pydantic-схемы заявок (Ticket) — по п. 3.5 и п. 4.3 ТЗ.

TicketCreate — тело POST /api/tickets (пользовательский путь, source всегда
    проставляется как WEB в сервисном слое, а не приходит с фронта).
TicketUpdate — тело PATCH /api/tickets/{id}, все поля опциональны.
TicketRead — тело ответа для списка и деталей, с вложенными объектами
    author/assignee/asset вместо голых ID (по аналогии с AssetRead).
TicketListResponse — обёртка {items, total} для GET /api/tickets.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ticket import TicketPriority, TicketSource, TicketStatus


class TicketPersonBrief(BaseModel):
    """Вложенный автор/исполнитель — минимальный набор полей для отображения."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class TicketAssetBrief(BaseModel):
    """Вложенный актив — минимальный набор полей, без полной карточки оборудования."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_number: str
    model: str | None


class TicketCreate(BaseModel):
    title: str
    description: str | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    asset_id: uuid.UUID | None = None


class TicketUpdate(BaseModel):
    """Частичное обновление — используется PATCH-эндпоинтом."""

    status: TicketStatus | None = None
    assignee_id: uuid.UUID | None = None
    resolution: str | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    priority: TicketPriority
    status: TicketStatus
    author: TicketPersonBrief
    assignee: TicketPersonBrief | None
    asset: TicketAssetBrief | None
    resolution: str | None
    source: TicketSource
    created_at: datetime
    closed_at: datetime | None


class TicketListResponse(BaseModel):
    """Обёртка для GET /api/tickets — {items, total} по аналогии с AssetListResponse."""

    items: list[TicketRead]
    total: int
