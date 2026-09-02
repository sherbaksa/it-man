"""
API-роут для справочника исполнителей заявок — мини-сессия B10b (unplanned).

GET /api/ticket-assignees — список активных пользователей с ролью Engineer или
IT-Head, отсортированный по full_name. Нужен фронтенду для выбора assignee_id
при назначении заявки (полный GET /api/users доступен только Admin — см.
users.py — этого недостаточно для сценария "IT-Head назначает Engineer").

Доступ: Engineer+ (Engineer, IT-Head, Admin) — те, кто вообще работает с заявками.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.ticket_assignee import TicketAssigneeRead

router = APIRouter(
    prefix="/api/ticket-assignees",
    tags=["ticket-assignees"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("", response_model=list[TicketAssigneeRead])
def get_ticket_assignees(db: Session = Depends(get_db)) -> list[User]:
    stmt = (
        select(User)
        .where(User.is_active.is_(True), User.role.in_([UserRole.ENGINEER, UserRole.IT_HEAD]))
        .order_by(User.full_name)
    )
    return list(db.scalars(stmt).all())
