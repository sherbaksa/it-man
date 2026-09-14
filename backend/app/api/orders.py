"""
API-роуты для Order (ОРД — организационно-распорядительные документы) — по
п. 4.4 и разделу 8 ТЗ.

GET /api/orders — список с фильтрами (status, type) и пагинацией.
POST /api/orders — создание черновика, статус всегда draft, автор — current_user.
PATCH /api/orders/{id} — частичное обновление: правка fields (только автор),
    смена status (автор — pending_approval/executed, согласующий — approved/rejected,
    в зависимости от DocumentTemplate.min_approver_role). Вся логика допустимости
    конкретного действия для конкретной роли — внутри order_service, здесь только
    маппинг исключений в HTTP-коды (по аналогии с api/tickets.py).

Доступ: Engineer+ (Engineer, IT-Head, Executive, Admin) — п. 1.3 ТЗ. В отличие
от tickets.py, сюда дополнительно включён Executive — он может быть
согласующим для Order с DocumentTemplate.min_approver_role=Executive (см.
order_service._APPROVER_RANKS), и без доступа к роутеру never смог бы дойти
до PATCH, чтобы согласовать документ.

GET /api/orders/{id}/render — появится в B15 (рендер через docxtpl), не здесь.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.document_template import DocumentTemplateType
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderListResponse, OrderRead, OrderUpdate
from app.services import order_service
from app.services.order_service import OrderInvalidTransitionError, OrderPermissionError

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[
        Depends(
            require_role(
                UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.EXECUTIVE, UserRole.ADMIN
            )
        )
    ],
)


@router.get("", response_model=OrderListResponse)
def get_orders(
    status_: OrderStatus | None = Query(None, alias="status"),
    type_: DocumentTemplateType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    items, total = order_service.list_orders(
        db,
        status=status_,
        type_=type_,
        page=page,
        page_size=page_size,
    )
    return OrderListResponse(items=[OrderRead.model_validate(item) for item in items], total=total)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    order = order_service.create_order(db, data, author_id=current_user.id)
    return OrderRead.model_validate(order)


@router.patch("/{order_id}", response_model=OrderRead)
def patch_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    """Роль Engineer+ (включая Executive) уже обеспечена dependencies роутера;
    точечная проверка "кто именно может это конкретное действие" (автор vs
    согласующий, с учётом min_approver_role) выполняется внутри order_service."""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    try:
        updated = order_service.update_order(db, order, data, current_user=current_user)
    except OrderPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except OrderInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return OrderRead.model_validate(updated)
