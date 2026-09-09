"""
Роутер /api/webhooks — общий вход для интеграционных вебхуков (n8n/Zabbix/
OpenProject, см. п. 4.6 ТЗ). Аутентификация — X-Webhook-Secret (без JWT),
переиспользует verify_webhook_secret() из core/dependencies.py (создана в B10
для /api/my/tickets).

B13: подключён только POST /zabbix. POST /n8n и POST /openproject появятся в
B18 при готовности соответствующих интеграций (см. согласованное в B13 решение
по вопросу №3 — задача в OpenProject создаётся не здесь, а на шаге интеграции).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import verify_webhook_secret
from app.schemas.ticket import TicketRead
from app.schemas.webhook import ZabbixWebhookPayload
from app.services.webhook_service import process_zabbix_webhook

router = APIRouter(
    prefix="/api/webhooks",
    tags=["webhooks"],
    dependencies=[Depends(verify_webhook_secret)],
)


@router.post("/zabbix", response_model=TicketRead | None, status_code=200)
def zabbix_webhook(payload: ZabbixWebhookPayload, db: Session = Depends(get_db)) -> TicketRead | None:
    """Принимает событие Zabbix Action -> Webhook. Обновляет MonitoringStatus;
    при status=PROBLEM и severity >= High — создаёт Ticket(source=zabbix_auto)
    и возвращает его. Иначе возвращает null (обновлён только мониторинг)."""
    ticket = process_zabbix_webhook(db, payload)
    return TicketRead.model_validate(ticket) if ticket else None
