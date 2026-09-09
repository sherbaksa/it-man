"""Сервисный слой для входящих интеграционных вебхуков (Zabbix; n8n/OpenProject
появятся в B18) — framework-agnostic, по п. 4.6, 6.1 ТЗ, сессия B13.

Архитектурное решение (согласовано в B13, отклонение от общего паттерна
"каждая функция сервиса коммитит сама"): апдейт MonitoringStatus + создание
Ticket + запись IntegrationLog описывают ОДНО событие Zabbix и должны быть
атомарны — единственный db.commit() в конце process_zabbix_webhook().
monitoring_service.upsert_monitoring_status() и
ticket_service.create_ticket_from_zabbix() поэтому не коммитят сами.
"""
from sqlalchemy.orm import Session

from app.models.integration_log import IntegrationDirection, IntegrationLog, IntegrationSystem
from app.models.monitoring_status import MonitoringHealthStatus
from app.models.ticket import Ticket, TicketPriority
from app.schemas.webhook import ZabbixProblemStatus, ZabbixSeverity, ZabbixWebhookPayload
from app.services import monitoring_service, ticket_service, user_service

# Числовой вес severity — та же шкала (0..5), что и Zabbix API, согласована с
# monitoring_service._CRITICAL_PRIORITY_THRESHOLD (B11): опрос (poll) и вебхук
# должны давать одинаковый MonitoringStatus для одного уровня проблемы.
_SEVERITY_WEIGHT: dict[ZabbixSeverity, int] = {
    ZabbixSeverity.NOT_CLASSIFIED: 0,
    ZabbixSeverity.INFORMATION: 1,
    ZabbixSeverity.WARNING: 2,
    ZabbixSeverity.AVERAGE: 3,
    ZabbixSeverity.HIGH: 4,
    ZabbixSeverity.DISASTER: 5,
}
_CRITICAL_WEIGHT_THRESHOLD = 3  # см. monitoring_service._CRITICAL_PRIORITY_THRESHOLD
_TICKET_WEIGHT_THRESHOLD = 4  # severity >= High создаёт Ticket — п. 4.6 ТЗ, согласовано в B13

_TICKET_PRIORITY_BY_SEVERITY: dict[ZabbixSeverity, TicketPriority] = {
    ZabbixSeverity.HIGH: TicketPriority.HIGH,
    ZabbixSeverity.DISASTER: TicketPriority.CRITICAL,
}

# Сентинел-идентификатор системного теневого пользователя — автор авто-тикетов
# Zabbix (вопрос №1, согласовано в B13); переиспользует get_or_create_shadow_user()
# (B10) без изменений в user_service.py.
ZABBIX_SYSTEM_MAX_USER_ID = "system:zabbix"
ZABBIX_SYSTEM_FULL_NAME = "Zabbix (автоматически)"


def _health_status_for(payload: ZabbixWebhookPayload) -> MonitoringHealthStatus:
    """RESOLVED -> ok независимо от severity (согласовано в B13); иначе по весу
    severity тем же порогом, что и polling-путь в monitoring_service (B11)."""
    if payload.status == ZabbixProblemStatus.RESOLVED:
        return MonitoringHealthStatus.OK
    weight = _SEVERITY_WEIGHT[payload.severity]
    if weight >= _CRITICAL_WEIGHT_THRESHOLD:
        return MonitoringHealthStatus.CRITICAL
    if weight == _SEVERITY_WEIGHT[ZabbixSeverity.WARNING]:
        return MonitoringHealthStatus.WARNING
    return MonitoringHealthStatus.OK


def _should_create_ticket(payload: ZabbixWebhookPayload) -> bool:
    return (
        payload.status == ZabbixProblemStatus.PROBLEM
        and _SEVERITY_WEIGHT[payload.severity] >= _TICKET_WEIGHT_THRESHOLD
    )


def process_zabbix_webhook(db: Session, payload: ZabbixWebhookPayload) -> Ticket | None:
    """Обрабатывает одно событие Zabbix Action -> Webhook:
    1) апдейт/создание MonitoringStatus (+ запись в MonitoringStatusHistory);
    2) при status=PROBLEM и severity >= High — создание Ticket(source=zabbix_auto);
    3) логирование в IntegrationLog(system=zabbix, direction=inbound).
    Единая транзакция — см. докстринг модуля."""
    health = _health_status_for(payload)
    monitoring_service.upsert_monitoring_status(
        db, host_identifier=payload.host, status=health, last_value=payload.problem_name,
    )

    ticket: Ticket | None = None
    if _should_create_ticket(payload):
        system_user = user_service.get_or_create_shadow_user(
            db, max_user_id=ZABBIX_SYSTEM_MAX_USER_ID, full_name=ZABBIX_SYSTEM_FULL_NAME,
        )
        ticket = ticket_service.create_ticket_from_zabbix(
            db,
            host_identifier=payload.host,
            problem_name=payload.problem_name,
            priority=_TICKET_PRIORITY_BY_SEVERITY[payload.severity],
            author_id=system_user.id,
        )

    db.add(
        IntegrationLog(
            system=IntegrationSystem.ZABBIX,
            direction=IntegrationDirection.INBOUND,
            endpoint="/api/webhooks/zabbix",
            status_code=200,
            payload=payload.model_dump(mode="json"),
            error_message=None,
        )
    )
    db.commit()
    if ticket is not None:
        db.refresh(ticket)
    return ticket
