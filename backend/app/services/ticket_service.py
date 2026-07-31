"""
Сервисный слой для Ticket — по п. 3.5 и п. 4.3 ТЗ, сессия B09 посессионного плана.

list_tickets() — листинг с фильтрами (status, assignee_id, priority) и пагинацией.
get_ticket() — получение одной заявки с подгруженными author/assignee/asset.
create_ticket() — создание заявки пользовательским (веб) путём: source всегда
    проставляется как WEB здесь, а не приходит из TicketCreate (см. обсуждение
    в сессии B09 — путь MAX/Zabbix появится отдельно в B18 через вебхуки).
update_ticket() — PATCH-семантика с двумя бизнес-правилами:
    1) нельзя перевести status=DONE без заполненного resolution;
    2) Engineer может менять только заявки, где он assignee; IT-Head/Admin — любые.
    closed_at проставляется автоматически при переходе в DONE/REJECTED (если ещё
    не заполнено) — решение принято в B09, в ТЗ явно не прописано, но логически
    следует из смысла поля.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketUpdate


class TicketResolutionRequiredError(Exception):
    """Поднимается при попытке перевести Ticket в status=done без заполненного
    resolution. Обрабатывается в api/tickets.py как 422 Unprocessable Entity —
    намеренно не HTTPException здесь, сервисный слой фреймворк-агностичен."""


class TicketPermissionError(Exception):
    """Поднимается, если Engineer пытается изменить заявку, где он не assignee.
    Обрабатывается в api/tickets.py как 403 Forbidden."""


def _apply_filters(
    query: Any,
    *,
    status: TicketStatus | None,
    assignee_id: uuid.UUID | None,
    priority: TicketPriority | None,
) -> Any:
    """Применяет общий набор фильтров и к count-запросу, и к запросу за данными —
    чтобы условия не расходились между total и items (по аналогии с asset_service)."""
    if status is not None:
        query = query.where(Ticket.status == status)
    if assignee_id is not None:
        query = query.where(Ticket.assignee_id == assignee_id)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    return query


def list_tickets(
    db: Session,
    *,
    status: TicketStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: TicketPriority | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    """Возвращает (items, total) с учётом фильтров и пагинации."""
    from sqlalchemy import func

    count_query = _apply_filters(
        select(func.count()).select_from(Ticket),
        status=status, assignee_id=assignee_id, priority=priority,
    )
    total = db.execute(count_query).scalar_one()

    query = select(Ticket).options(
        selectinload(Ticket.author),
        selectinload(Ticket.assignee),
        selectinload(Ticket.asset),
    )
    query = _apply_filters(query, status=status, assignee_id=assignee_id, priority=priority)
    query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(query).scalars().all())

    return items, total


def get_ticket(db: Session, ticket_id: uuid.UUID) -> Ticket | None:
    """Возвращает заявку по id с подгруженными author/assignee/asset."""
    query = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.author),
            selectinload(Ticket.assignee),
            selectinload(Ticket.asset),
        )
    )
    return db.execute(query).scalar_one_or_none()


def create_ticket(db: Session, data: TicketCreate, author_id: uuid.UUID) -> Ticket:
    """Создаёт заявку пользовательским (веб) путём. source всегда WEB — заявки
    с source=max/zabbix_auto создаются отдельным путём через вебхуки (B18),
    минуя эту функцию."""
    from app.models.ticket import TicketSource

    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        asset_id=data.asset_id,
        author_id=author_id,
        source=TicketSource.WEB,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket(
    db: Session,
    ticket: Ticket,
    data: TicketUpdate,
    current_user: User,
) -> Ticket:
    """Частично обновляет заявку (PATCH-семантика — только переданные поля).

    Порядок проверок (до мутации ticket и до db.commit()):
      1. Права: Engineer может менять заявку, если она уже назначена на него
         (ticket.assignee_id == current_user.id), ЛИБО если заявка ещё никому
         не назначена и в этом же запросе Engineer берёт её на себя
         (self-assign: assignee_id было None, становится current_user.id).
         Engineer не может переназначить заявку на другого исполнителя или
         забрать чужую. IT-Head/Admin — без ограничений (любые заявки).
      2. Бизнес-правило: status=done требует непустого resolution (учитывается
         как уже сохранённое значение, так и переданное в этом же запросе).
    """
    update_data = data.model_dump(exclude_unset=True)

    if current_user.role == UserRole.ENGINEER:
        is_own_ticket = ticket.assignee_id == current_user.id
        is_self_assign = (
            ticket.assignee_id is None
            and update_data.get("assignee_id") == current_user.id
        )
        if not (is_own_ticket or is_self_assign):
            raise TicketPermissionError(
                "Engineer может изменять только свои назначенные заявки "
                "или взять в работу ещё не назначенную"
            )

    if update_data.get("status") == TicketStatus.DONE:
        resolution = update_data.get("resolution", ticket.resolution)
        if not resolution:
            raise TicketResolutionRequiredError(
                "Нельзя закрыть заявку без заполненного resolution"
            )

    for field, value in update_data.items():
        setattr(ticket, field, value)

    if ticket.status in (TicketStatus.DONE, TicketStatus.REJECTED) and ticket.closed_at is None:
        ticket.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(ticket)
    return ticket
