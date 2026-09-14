"""
Pydantic-схемы заявок на согласование документов (Order) — по п. 3.6, 4.4 и разделу 8 ТЗ.

OrderCreate — тело POST /api/orders (author_id и status всегда проставляются
    сервисным слоем: author_id — из current_user, status — всегда draft).
OrderUpdate — тело PATCH /api/orders/{id}. Обрабатываются два независимых
    сценария (проверяются в order_service, а не здесь):
      - автор редактирует `fields` в статусе draft (или отправляет на согласование,
        передав status=pending_approval)
      - согласующий выставляет status=approved/rejected, либо исполнитель — executed
    Оба сценария используют одну и ту же схему с опциональными полями.
OrderRead — тело ответа для списка и деталей, с вложенными author/approver/template
    вместо голых ID (по аналогии с TicketRead).
OrderListResponse — обёртка {items, total} для GET /api/orders.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document_template import DocumentTemplateType
from app.models.order import OrderStatus


class OrderPersonBrief(BaseModel):
    """Вложенный автор/согласующий — минимальный набор полей для отображения."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class OrderTemplateBrief(BaseModel):
    """Вложенный шаблон документа — без file_path (внутренняя деталь рендера)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: DocumentTemplateType
    field_schema: dict


class OrderCreate(BaseModel):
    type: DocumentTemplateType
    template_id: uuid.UUID
    fields: dict


class OrderUpdate(BaseModel):
    """Частичное обновление — используется PATCH-эндпоинтом.

    fields — правка автора (допустима в draft; в pending_approval вызывает
        сброс в draft и инкремент version в order_service).
    status — переход, инициированный либо автором (pending_approval),
        либо согласующим (approved/rejected), либо исполнителем (executed).
        Валидность конкретного перехода для конкретной роли проверяется
        в order_service, а не на уровне схемы.
    """

    fields: dict | None = None
    status: OrderStatus | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: DocumentTemplateType
    template: OrderTemplateBrief
    fields: dict
    status: OrderStatus
    author: OrderPersonBrief
    approver: OrderPersonBrief | None
    created_at: datetime
    approved_at: datetime | None
    version: int


class OrderListResponse(BaseModel):
    """Обёртка для GET /api/orders — {items, total} по аналогии с TicketListResponse."""

    items: list[OrderRead]
    total: int


class OrderHistoryRead(BaseModel):
    """Один снапшот версии Order из OrderHistory — для Timeline на карточке
    документа (GET /api/orders/{id}/history).

    changed_by_user назван по имени ORM-связи (order_history.py:
    changed_by_user), а не по имени FK-колонки (changed_by) — так
    from_attributes подхватывает вложенный объект User напрямую."""

    model_config = ConfigDict(from_attributes=True)

    version: int
    fields: dict
    changed_by_user: OrderPersonBrief
    changed_at: datetime
