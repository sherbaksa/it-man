"""
API-роут /api/my/tickets (B10) — доступ роли User через MAX-бота, п. 4.3 ТЗ.

Не входит в общий роутер tickets.py (там router-level Depends(require_role(...))
завязан на JWT-роли Engineer+ — сюда, наоборот, попадают запросы от n8n от лица
MAX-пользователя, без JWT). Аутентификация — X-Webhook-Secret (п. 4.6 ТЗ),
временно переиспользуем тот же механизм, что и для будущих вебхуков n8n/Zabbix (B18).

Порядок работы:
1. n8n передаёт max_user_id (обязателен) и, если удалось получить, phone/full_name.
2. get_or_create_shadow_user находит или создаёт пользователя (роль User).
3. Возвращаются только его заявки (author_id == найденный/созданный пользователь).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import verify_webhook_secret
from app.schemas.ticket import TicketListResponse, TicketRead
from app.services import ticket_service, user_service

router = APIRouter(
    prefix="/api/my",
    tags=["my-tickets"],
    dependencies=[Depends(verify_webhook_secret)],
)


@router.get("/tickets", response_model=TicketListResponse)
def get_my_tickets(
    max_user_id: str = Query(..., description="message.sender.user_id из MAX"),
    full_name: str | None = Query(None, description="message.sender.name из MAX"),
    phone: str | None = Query(None, description="Телефон, если известен (обычно отсутствует)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    user = user_service.get_or_create_shadow_user(
        db, max_user_id=max_user_id, full_name=full_name, phone=phone,
    )
    items, total = ticket_service.list_tickets(
        db, author_id=user.id, page=page, page_size=page_size,
    )
    return TicketListResponse(items=[TicketRead.model_validate(item) for item in items], total=total)
