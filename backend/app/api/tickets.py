"""
API-роуты для Ticket (заявки) — по п. 4.3 ТЗ.

GET /api/tickets — список с фильтрами (status, assignee_id, priority) и пагинацией.
GET /api/tickets/{id} — детальная карточка заявки.
POST /api/tickets — создание пользовательским (веб) путём, source всегда WEB.
    Сервисный вызов без пользовательской авторизации (для вебхука n8n, source=max)
    появится отдельно в B18 — не в этом роутере.
PATCH /api/tickets/{id} — частичное обновление: Engineer — только свои назначенные
    заявки, IT-Head/Admin — любые (проверка внутри ticket_service, т.к. зависит
    от данных конкретной заявки, а не только от роли).

Доступ: Engineer+ (Engineer, IT-Head, Admin) — см. п. 1.3 ТЗ "Роли и права доступа".
/api/my/tickets (доступ User через MAX-бота) — отдельный узкий эндпоинт, сессия B10.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.ticket import TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketListResponse, TicketRead, TicketUpdate
from app.services import ticket_service
from app.services.ticket_service import TicketPermissionError, TicketResolutionRequiredError

router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("", response_model=TicketListResponse)
def get_tickets(
    status_: TicketStatus | None = Query(None, alias="status"),
    assignee_id: uuid.UUID | None = None,
    priority: TicketPriority | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    items, total = ticket_service.list_tickets(
        db,
        status=status_,
        assignee_id=assignee_id,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    return TicketListResponse(items=[TicketRead.model_validate(item) for item in items], total=total)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db)) -> TicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return TicketRead.model_validate(ticket)


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketRead:
    ticket = ticket_service.create_ticket(db, data, author_id=current_user.id)
    return TicketRead.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketRead)
def patch_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketRead:
    """Роль Engineer+ уже обеспечена dependencies роутера; точечная проверка
    "Engineer — только свои назначенные" выполняется внутри ticket_service,
    т.к. зависит от assignee_id конкретной заявки."""
    ticket = ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    try:
        updated = ticket_service.update_ticket(db, ticket, data, current_user=current_user)
    except TicketPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TicketResolutionRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return TicketRead.model_validate(updated)
